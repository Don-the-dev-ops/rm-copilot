"""
RM Copilot, Phase 5 Lab 13: load the Gold CSVs into Azure SQL.

For each Gold table:
  1. read exports/gold/<table>.csv
  2. check it: not empty, key column has no blanks and no duplicates
  3. empty stg.<table> and copy every CSV row into it
  4. check the stockroom: rows staged == rows in the file
  5. MERGE stg.<table> into serve.<table> (insert new, update changed, delete gone)
  6. write one row to serve.load_log

Steps 5 and 6 run in one transaction: either the shelves change AND the log says so, or nothing changes.
If any check fails, serve.<table> is not touched and the log row says "failed".

Safe to re-run: a second run with the same CSVs inserts 0, updates 0, deletes 0.
Sign-in: your `az login` session (Microsoft Entra). No passwords.

Run from the repo root:  python serving/load_gold_to_sql.py
"""

import os
import struct
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyodbc
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# ----------------------------------------------------------------------------- settings
HERE = Path(__file__).resolve().parent              # .../rm-copilot/serving
REPO = HERE.parent                                  # .../rm-copilot
load_dotenv(HERE / ".env")

SQL_SERVER = os.environ["SQL_SERVER"]               # sql-rmcopilot-dh01.database.windows.net
SQL_DATABASE = os.environ["SQL_DATABASE"]           # rmcopilot
GOLD_DIR = REPO / os.getenv("EXPORTS_DIR", "exports") / "gold"

# Load order and the key that makes each row unique.
TABLES = {
    "client_360": "client_id",
    "client_signals": "client_id",
    "anomaly_transactions": "txn_id",
}


# ----------------------------------------------------------------------------- connect
def connect() -> pyodbc.Connection:
    """Open a connection using a token from `az login`. Retries while a paused database wakes up."""
    token = AzureCliCredential().get_token("https://database.windows.net/.default").token
    raw = token.encode("utf-16-le")
    token_struct = struct.pack(f"<I{len(raw)}s", len(raw), raw)   # the shape ODBC expects
    SQL_COPT_SS_ACCESS_TOKEN = 1256                                 # "here is a token" option

    conn_str = (
        "Driver={ODBC Driver 18 for SQL Server};"
        f"Server=tcp:{SQL_SERVER},1433;Database={SQL_DATABASE};"
        "Encrypt=yes;TrustServerCertificate=no;Connection Timeout=60;"
    )
    for attempt in range(1, 5):
        try:
            return pyodbc.connect(conn_str, attrs_before={SQL_COPT_SS_ACCESS_TOKEN: token_struct},
                                  autocommit=False)
        except pyodbc.Error as err:
            # 40613 = database is waking up from auto-pause; give it time and try again
            if "40613" in str(err) and attempt < 4:
                print(f"  database is waking up, waiting 20s (attempt {attempt}/4)...")
                time.sleep(20)
                continue
            raise


# ----------------------------------------------------------------------------- read and check the CSV
def staging_columns(cur, table: str) -> list[tuple[str, str]]:
    """Column names and SQL types of stg.<table>, in table order. The table is the contract."""
    cur.execute(
        "SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_SCHEMA = 'stg' AND TABLE_NAME = ? ORDER BY ORDINAL_POSITION", table)
    return [(r.COLUMN_NAME, r.DATA_TYPE) for r in cur.fetchall()]


def read_csv(path: Path, columns: list[tuple[str, str]]) -> pd.DataFrame:
    """Read the CSV as text, then convert each column to the type its staging column expects."""
    df = pd.read_csv(path, dtype=str, keep_default_na=False, na_values=[""])
    expected = [name for name, _ in columns]
    missing = [c for c in expected if c not in df.columns]
    extra = [c for c in df.columns if c not in expected]
    if missing or extra:
        raise ValueError(f"columns differ from stg table. missing={missing} extra={extra}")
    df = df[expected]                                           # same order as the table

    for name, sql_type in columns:
        col = df[name]
        if sql_type == "bit":
            # pandas wrote Spark booleans as True/False
            df[name] = col.map({"True": True, "False": False, "true": True, "false": False})
        elif sql_type in ("int", "bigint"):
            # an int column with blanks comes out of pandas as "10.0", so go through float first
            df[name] = pd.to_numeric(col).round().astype("Int64")
        elif sql_type in ("decimal", "numeric", "float"):
            df[name] = pd.to_numeric(col)
        elif sql_type == "date":
            df[name] = pd.to_datetime(col, format="ISO8601").dt.date
        elif sql_type in ("datetime2", "datetime"):
            df[name] = pd.to_datetime(col, utc=True, format="ISO8601").dt.tz_localize(None).dt.floor("s")
        # text columns stay as they are
    return df


def check_csv(df: pd.DataFrame, key: str) -> None:
    if len(df) == 0:
        raise ValueError("file has no rows")
    blanks = int(df[key].isna().sum())
    if blanks:
        raise ValueError(f"{blanks} rows have a blank {key}")
    dupes = int(df[key].duplicated().sum())
    if dupes:
        example = df.loc[df[key].duplicated(), key].iloc[0]
        raise ValueError(f"{dupes} duplicate {key} values, e.g. {example}")


# ----------------------------------------------------------------------------- stage
def stage(cur, table: str, df: pd.DataFrame) -> int:
    """Empty the stockroom and copy every row in. Returns rows staged."""
    cur.execute(f"TRUNCATE TABLE stg.{table}")
    cols = ", ".join(df.columns)
    marks = ", ".join("?" for _ in df.columns)
    rows = df.astype(object).where(df.notna(), None).values.tolist()   # NaN/NA -> NULL
    rows = [[v.to_pydatetime() if isinstance(v, pd.Timestamp) else v for v in r] for r in rows]
    cur.fast_executemany = True                                         # send rows in big batches
    cur.executemany(f"INSERT INTO stg.{table} ({cols}) VALUES ({marks})", rows)
    cur.execute(f"SELECT COUNT(*) FROM stg.{table}")
    return cur.fetchone()[0]


# ----------------------------------------------------------------------------- merge
def merge(cur, table: str, key: str, columns: list[str]) -> dict:
    """Make serve.<table> match stg.<table>. Returns counts of inserted / updated / deleted rows."""
    non_key = [c for c in columns if c != key]
    set_list = ",\n            ".join(f"t.{c} = s.{c}" for c in non_key) + ",\n            t._loaded_at = SYSUTCDATETIME()"
    s_cols = ", ".join(f"s.{c}" for c in non_key)
    t_cols = ", ".join(f"t.{c}" for c in non_key)
    all_cols = ", ".join(columns)
    all_s = ", ".join(f"s.{c}" for c in columns)

    # "EXISTS (SELECT s... EXCEPT SELECT t...)" is true only when at least one value really changed,
    # and it treats NULL = NULL as equal. So unchanged rows are left alone and a re-run updates 0.
    sql = f"""
    SET NOCOUNT ON;                          -- only the final SELECT sends rows back
    DECLARE @changes TABLE (action NVARCHAR(10));
    MERGE serve.{table} AS t
    USING stg.{table} AS s
       ON t.{key} = s.{key}
    WHEN MATCHED AND EXISTS (SELECT {s_cols} EXCEPT SELECT {t_cols}) THEN
        UPDATE SET
            {set_list}
    WHEN NOT MATCHED BY TARGET THEN
        INSERT ({all_cols}) VALUES ({all_s})
    WHEN NOT MATCHED BY SOURCE THEN
        DELETE
    OUTPUT $action INTO @changes;
    SELECT SUM(CASE WHEN action = 'INSERT' THEN 1 ELSE 0 END),
           SUM(CASE WHEN action = 'UPDATE' THEN 1 ELSE 0 END),
           SUM(CASE WHEN action = 'DELETE' THEN 1 ELSE 0 END)
    FROM @changes;
    """
    cur.execute(sql)
    while cur.description is None and cur.nextset():   # step past any non-row results
        pass
    ins, upd, dele = cur.fetchone()
    return {"inserted": ins or 0, "updated": upd or 0, "deleted": dele or 0}


# ----------------------------------------------------------------------------- log
def log(cur, run_id, table, path, started, status, message=None, rows_in=None, staged=None, counts=None):
    counts = counts or {}
    cur.execute(
        "INSERT INTO serve.load_log (run_id, table_name, source_file, rows_in_file, rows_staged, "
        "rows_inserted, rows_updated, rows_deleted, status, message, started_at, finished_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, SYSUTCDATETIME())",
        run_id, table, str(path.relative_to(REPO)), rows_in, staged,
        counts.get("inserted"), counts.get("updated"), counts.get("deleted"),
        status, (message or "")[:400] or None, started)


# ----------------------------------------------------------------------------- main
def main() -> int:
    run_id = str(uuid.uuid4())
    print(f"Run {run_id}")
    print(f"Reading CSVs from {GOLD_DIR}")
    conn = connect()
    cur = conn.cursor()
    failures = 0

    for table, key in TABLES.items():
        path = GOLD_DIR / f"{table}.csv"
        started = datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)
        rows_in = staged = None
        print(f"\n{table}")
        try:
            if not path.exists():
                raise FileNotFoundError(f"missing file {path}")
            columns = staging_columns(cur, table)
            if not columns:
                raise ValueError(f"stg.{table} does not exist (run serving/sql/02_tables.sql)")

            df = read_csv(path, columns)
            rows_in = len(df)
            check_csv(df, key)
            print(f"  file: {rows_in:,} rows, {key} unique")

            staged = stage(cur, table, df)
            if staged != rows_in:
                raise ValueError(f"staged {staged} rows but the file has {rows_in}")
            print(f"  staged: {staged:,} rows")

            counts = merge(cur, table, key, list(df.columns))
            log(cur, run_id, table, path, started, "success", None, rows_in, staged, counts)
            conn.commit()                                   # shelves and log change together
            print(f"  merged: {counts['inserted']} inserted, {counts['updated']} updated, "
                  f"{counts['deleted']} deleted")

        except Exception as err:
            conn.rollback()                                 # serve.<table> stays as it was
            failures += 1
            print(f"  FAILED: {err}")
            log(cur, run_id, table, path, started, "failed", str(err), rows_in, staged)
            conn.commit()

    cur.close()
    conn.close()                                            # close so the database can auto-pause
    print("\nDone." if failures == 0 else f"\nFinished with {failures} failed table(s).")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

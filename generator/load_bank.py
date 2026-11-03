"""
RM Copilot - Lab 2: load the Bronze files into a local SQLite database.

Reads out/bronze/ (never out/ground_truth/) and writes bank.db, so you can practise
SQL on your synthetic bank. SQLite ships with Python: nothing to install.

    python load_bank.py --run-date 2026-10-07

Re-running replaces bank.db, so it always matches the files in out/bronze.
"""

import argparse
import csv
import json
import sqlite3
from pathlib import Path

# Column types per table. Anything not listed is TEXT.
NUMERIC = {
    "clients": {"monthly_income_zar": "REAL"},
    "accounts": {"balance": "REAL"},
    "cards": {"credit_limit_zar": "REAL"},
    "loans": {"principal_zar": "REAL", "outstanding_zar": "REAL", "interest_rate_pct": "REAL"},
    "transactions": {"amount_zar": "REAL"},
}
KEYS = {"relationship_managers": "rm_id", "clients": "client_id", "accounts": "account_id",
        "cards": "card_id", "loans": "loan_id", "transactions": "txn_id"}


def create(db, table, columns):
    types = NUMERIC.get(table, {})
    cols = ", ".join(f"{c} {types.get(c, 'TEXT')}{' PRIMARY KEY' if c == KEYS[table] else ''}" for c in columns)
    db.execute(f"DROP TABLE IF EXISTS {table}")
    db.execute(f"CREATE TABLE {table} ({cols})")


def insert(db, table, columns, rows):
    types = NUMERIC.get(table, {})
    def value(c, v):
        if v in ("", None):
            return None  # empty CSV cell = missing value (e.g. a debit card has no credit limit)
        return float(v) if c in types else v
    db.executemany(f"INSERT INTO {table} VALUES ({', '.join('?' * len(columns))})",
                   ([value(c, r.get(c)) for c in columns] for r in rows))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--run-date", required=True)
    p.add_argument("--out", default="out")
    p.add_argument("--db", default="bank.db")
    a = p.parse_args()
    bronze = Path(a.out) / "bronze"

    db = sqlite3.connect(a.db)
    for table in ["relationship_managers", "clients", "accounts", "cards", "loans"]:
        with (bronze / table / f"{a.run_date}.csv").open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            create(db, table, reader.fieldnames)
            insert(db, table, reader.fieldnames, reader)

    with (bronze / "transactions" / f"{a.run_date}.jsonl").open(encoding="utf-8") as f:
        first = json.loads(f.readline())
        columns = list(first)
        create(db, "transactions", columns)
        f.seek(0)
        insert(db, "transactions", columns, (json.loads(line) for line in f))

    # Indexes make the joins in the lab fast (seconds instead of minutes)
    db.execute("CREATE INDEX idx_txn_account ON transactions(account_id)")
    db.execute("CREATE INDEX idx_acct_client ON accounts(client_id)")
    db.commit()

    for table in KEYS:
        n = db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"{table:24s} {n:>9,} rows")
    print(f"\nLoaded into {a.db}")

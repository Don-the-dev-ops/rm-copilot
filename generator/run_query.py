"""
RM Copilot - Lab 2: run a .sql file against bank.db and show the result.

    python run_query.py queries/01_warmup.sql
    python run_query.py queries/hunt_idle_cash.sql --save answers/idle_cash.csv

--save writes every row to a CSV, which score_answers.py then marks.
"""

import argparse
import csv
import sqlite3
import sys
import time
from pathlib import Path

p = argparse.ArgumentParser()
p.add_argument("sql_file")
p.add_argument("--db", default="bank.db")
p.add_argument("--save", help="write the full result to this CSV")
p.add_argument("--show", type=int, default=15, help="rows to print")
a = p.parse_args()

if not Path(a.db).exists():
    sys.exit(f"{a.db} not found: run load_bank.py first")

sql = Path(a.sql_file).read_text(encoding="utf-8")
start = time.time()
cur = sqlite3.connect(a.db).execute(sql)
headers = [d[0] for d in cur.description]
rows = cur.fetchall()

fmt = lambda v: f"{v:,.2f}" if isinstance(v, float) else str(v)
widths = [max([len(h)] + [len(fmt(r[i])) for r in rows[:a.show]]) for i, h in enumerate(headers)]
print("  ".join(h.ljust(w) for h, w in zip(headers, widths)))
print("  ".join("-" * w for w in widths))
for r in rows[:a.show]:
    print("  ".join(fmt(v).ljust(w) for v, w in zip(r, widths)))
print(f"\n{len(rows):,} row{'' if len(rows) == 1 else 's'} in {time.time() - start:.1f}s" + (f" (showing first {a.show})" if len(rows) > a.show else ""))

if a.save:
    Path(a.save).parent.mkdir(parents=True, exist_ok=True)
    with open(a.save, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(headers)
        w.writerows(rows)
    print(f"Saved to {a.save}")

"""
RM Copilot - Lab 2: mark your SQL answers against the answer key.

    python score_answers.py answers/idle_cash.csv --story idle_cash --run-date 2026-10-07
    python score_answers.py answers/anomaly.csv   --story anomaly   --run-date 2026-10-07

Your CSV needs a client_id column (or txn_id for --story anomaly). Other columns are ignored.
This is the ONLY script that opens out/ground_truth: your queries never see the answers.
"""

import argparse
import csv
import sys
from pathlib import Path

STORIES = ["idle_cash", "forex_growth", "upgrade_candidate", "anomaly", "salary_increase"]

p = argparse.ArgumentParser()
p.add_argument("answers")
p.add_argument("--story", required=True, choices=STORIES)
p.add_argument("--run-date", required=True)
p.add_argument("--out", default="out")
a = p.parse_args()

truth_dir = Path(a.out) / "ground_truth"
key = "txn_id" if a.story == "anomaly" else "client_id"

with open(a.answers, encoding="utf-8") as f:
    reader = csv.DictReader(f)
    if key not in (reader.fieldnames or []):
        sys.exit(f"{a.answers} needs a '{key}' column; it has: {', '.join(reader.fieldnames or [])}")
    guessed = {r[key] for r in reader}

if a.story == "anomaly":
    with (truth_dir / "planted_anomalies" / f"{a.run_date}.csv").open(encoding="utf-8") as f:
        actual = {r["txn_id"] for r in csv.DictReader(f)}
    thing = "transactions"
else:
    with (truth_dir / "client_stories" / f"{a.run_date}.csv").open(encoding="utf-8") as f:
        actual = {r["client_id"] for r in csv.DictReader(f) if r["story"] == a.story}
    thing = "clients"

found = guessed & actual
false_alarms = guessed - actual
missed = actual - guessed
precision = len(found) / len(guessed) if guessed else 0
recall = len(found) / len(actual) if actual else 0

print(f"Story: {a.story}")
print(f"  You flagged     {len(guessed):>5,} {thing}")
print(f"  Really {a.story:<9}{len(actual):>5,}")
print(f"  Correct         {len(found):>5,}")
print(f"  False alarms    {len(false_alarms):>5,}   (flagged, but not this story)")
print(f"  Missed          {len(missed):>5,}   (this story, but not flagged)")
print(f"\n  Precision {precision:6.1%}   of the ones you flagged, how many were right")
print(f"  Recall    {recall:6.1%}   of the real ones, how many you found") 
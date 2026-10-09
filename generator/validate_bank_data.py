"""
RM Copilot - Phase 1 realism checks for the synthetic bank.

Reads the files generate_bank_data.py wrote and fails loudly when the data breaks a
rule a real bank would never break. Run it after every generator change:

    python generate_bank_data.py --months 12 --seed 42 --run-date 2026-10-07
    python validate_bank_data.py --months 12 --run-date 2026-10-07

Exit code 0 = every check passed, 1 = at least one failed (so CI can block a bad change).

Four kinds of check:
  integrity    every key points at a row that exists; same seed gives the same bank
  realism      numbers and dates make sense together (the principles in the lesson)
  signal       planted stories are clearly visible, so later phases can find them
  leak         no single column gives a planted story away, so finding them is a real test

Ground truth (which clients got which story, which transactions are planted anomalies) is
read from out/ground_truth/, which the generator keeps out of the Bronze tables.

The limits below are independent lending norms, not copies of the generator's settings:
a check that only repeats the generator's own numbers can't catch the generator being wrong.
"""

import argparse
import csv
import json
import statistics
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

MAX_HOME_LOAN_X_ANNUAL_INCOME = 4.0     # SA banks rarely lend more than ~4x gross annual income
MAX_VEHICLE_X_ANNUAL_INCOME = 1.0
MAX_DEBT_SERVICE_SHARE = 0.40           # all loan instalments vs gross monthly income
LOAN_TERM_MONTHS = {"Home loan": 240, "Vehicle finance": 72}
TFSA_ANNUAL_LIMITS = {**{y: 30_000 for y in (2015, 2016)}, **{y: 33_000 for y in (2017, 2018, 2019)},
                      **{y: 36_000 for y in range(2020, 2026)}, 2026: 46_000}
TFSA_LIFETIME = 500_000
CREDIT_LIMIT_X_INCOME = 2.5
INCOME_BANDS = {"Private Banking": (58_000, 91_999), "Signature": (92_000, 260_000)}
STORY_SHARES = {"none": 0.63, "idle_cash": 0.12, "forex_growth": 0.12, "upgrade_candidate": 0.10, "anomaly": 0.03}


class Report:
    def __init__(self):
        self.results = []

    def check(self, kind, name, failures, total, show=3):
        ok = not failures and total > 0  # a check over zero rows proves nothing, so it fails
        self.results.append(ok)
        print(f"[{'PASS' if ok else 'FAIL'}] {kind:9s} {name}  ({total - len(failures):,}/{total:,} ok)")
        for f in (failures or (["no rows to check"] if total == 0 else []))[:show]:
            print(f"         e.g. {f}")


def load(folder: Path, run_date: str):
    def csv_rows(t):
        with (folder / t / f"{run_date}.csv").open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    tables = {t: csv_rows(t) for t in ["relationship_managers", "clients", "accounts", "cards", "loans"]}
    with (folder / "transactions" / f"{run_date}.jsonl").open(encoding="utf-8") as f:
        tables["transactions"] = [json.loads(line) for line in f]
    return tables


def load_truth(folder: Path, run_date: str):
    """The answer key lives outside Bronze, in out/ground_truth/."""
    def rows(t):
        with (folder / t / f"{run_date}.csv").open(encoding="utf-8") as f:
            return list(csv.DictReader(f))
    story = {r["client_id"]: r["story"] for r in rows("client_stories")}
    planted = {r["txn_id"] for r in rows("planted_anomalies")}
    return story, planted


def instalment(principal, rate_pct, months):
    r = rate_pct / 100 / 12
    return principal * r / (1 - (1 + r) ** -months)


def years_between(a: date, b: date) -> float:
    return (b - a).days / 365.25


def birthday(d: date, years: int) -> date:
    """Calendar date of the given birthday (dividing days by 365.25 misjudges exact birthdays)."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # born 29 February
        return d.replace(year=d.year + years, day=28)


def run_checks(t, story, planted_ids, run_date: date, months: int, rep: Report):
    clients = {c["client_id"]: c for c in t["clients"]}
    accounts = {a["account_id"]: a for a in t["accounts"]}
    cards = {c["card_id"]: c for c in t["cards"]}
    txns = t["transactions"]
    rm_ids = {r["rm_id"] for r in t["relationship_managers"]}
    income = {cid: float(c["monthly_income_zar"]) for cid, c in clients.items()}
    since = {cid: date.fromisoformat(c["client_since"]) for cid, c in clients.items()}
    acct_client = {aid: a["client_id"] for aid, a in accounts.items()}
    history_start = run_date - timedelta(days=30 * months)
    tday = lambda x: date.fromisoformat(x["txn_ts"][:10])

    # ---------- integrity ----------
    rep.check("integrity", "client.rm_id exists",
              [c["client_id"] for c in clients.values() if c["rm_id"] not in rm_ids], len(clients))
    rep.check("integrity", "account.client_id exists",
              [a["account_id"] for a in accounts.values() if a["client_id"] not in clients], len(accounts))
    rep.check("integrity", "card.account_id exists",
              [c["card_id"] for c in cards.values() if c["account_id"] not in accounts], len(cards))
    rep.check("integrity", "loan.client_id exists",
              [l["loan_id"] for l in t["loans"] if l["client_id"] not in clients], len(t["loans"]))
    bad = [x["txn_id"] for x in txns if x["account_id"] not in accounts
           or (x["card_id"] and (x["card_id"] not in cards or cards[x["card_id"]]["account_id"] != x["account_id"]))]
    rep.check("integrity", "transaction keys exist and card belongs to account", bad, len(txns))
    ids = [x["txn_id"] for x in txns]
    rep.check("integrity", "transaction IDs unique", [] if len(ids) == len(set(ids)) else ["duplicate IDs"], len(ids))
    leaked = [f"{table}.{col}" for table, rows in t.items() if rows for col in rows[0]
              if col.startswith("_") or col in ("story", "label")]
    rep.check("integrity", "Bronze holds no answer-key columns", leaked, len(t))
    emails = [c["email"] for c in clients.values()]
    rep.check("integrity", "client emails unique", [] if len(emails) == len(set(emails)) else
              [f"{len(emails) - len(set(emails))} duplicates"], len(emails))

    # ---------- realism: people, products and dates ----------
    rep.check("realism", "clients were at least 21 when they joined",
              [c["client_id"] for c in clients.values()
               if since[c["client_id"]] < birthday(date.fromisoformat(c["date_of_birth"]), 21)], len(clients))
    rep.check("realism", "clients joined before the transaction history starts",
              [c["client_id"] for c in clients.values() if since[c["client_id"]] >= history_start], len(clients))
    rep.check("realism", "risk profile assessed after joining",
              [c["client_id"] for c in clients.values()
               if not since[c["client_id"]] <= date.fromisoformat(c["risk_profile_date"]) <= run_date], len(clients))

    fails = []
    for c in clients.values():
        lo, hi = INCOME_BANDS[c["segment"]]
        inc = income[c["client_id"]]
        if story[c["client_id"]] == "upgrade_candidate":
            if not (c["segment"] == "Private Banking" and INCOME_BANDS["Signature"][0] <= inc <= 140_000):
                fails.append(f"{c['client_id']} upgrade candidate on {c['segment']}, R{inc:,.0f}")
        elif not lo <= inc <= hi:
            fails.append(f"{c['client_id']} {c['segment']} on R{inc:,.0f}")
    rep.check("realism", "income inside the segment's band (upgrade candidates: PB, R92k-R140k)", fails, len(clients))

    rep.check("realism", "accounts opened after the client joined, not in the future",
              [f"{a['account_id']} {a['product']} opened {a['opened_date']}" for a in accounts.values()
               if not since[a["client_id"]] <= date.fromisoformat(a["opened_date"]) <= run_date], len(accounts))

    fails, n = [], 0
    for a in accounts.values():
        if a["product"] != "Tax-Free Savings":
            continue
        n += 1
        opened = date.fromisoformat(a["opened_date"])
        first = opened.year if opened.month >= 3 else opened.year - 1
        last = run_date.year if run_date.month >= 3 else run_date.year - 1
        latest = TFSA_ANNUAL_LIMITS[max(TFSA_ANNUAL_LIMITS)]
        max_contrib = min(TFSA_LIFETIME, sum(TFSA_ANNUAL_LIMITS.get(y, latest) for y in range(first, last + 1)))
        if float(a["balance"]) > max_contrib * (1 + 0.08 * years_between(opened, run_date)):
            fails.append(f"{a['account_id']} R{float(a['balance']):,.0f}, max contributions R{max_contrib:,.0f}")
    rep.check("realism", "TFSA balance possible within contribution limits plus 8%/yr growth", fails, n)

    rep.check("realism", "credit limit = 2.5 x monthly income",
              [c["card_id"] for c in cards.values() if c["card_type"] == "Platinum Credit"
               and abs(float(c["credit_limit_zar"]) - CREDIT_LIMIT_X_INCOME * income[acct_client[c["account_id"]]]) > 1_000],
              sum(c["card_type"] != "Debit" for c in cards.values()))

    # ---------- realism: loans ----------
    fails, debt = [], defaultdict(float)
    for l in t["loans"]:
        cid, principal = l["client_id"], float(l["principal_zar"])
        cap = MAX_HOME_LOAN_X_ANNUAL_INCOME if l["loan_type"] == "Home loan" else MAX_VEHICLE_X_ANNUAL_INCOME
        if principal > cap * income[cid] * 12:
            fails.append(f"{l['loan_id']} {l['loan_type']} R{principal:,.0f} = {principal / (income[cid] * 12):.1f}x annual income")
        debt[cid] += instalment(principal, float(l["interest_rate_pct"]), LOAN_TERM_MONTHS[l["loan_type"]])
    rep.check("realism", "loan size within lending multiples of income", fails, len(t["loans"]))
    rep.check("realism", f"loan instalments under {MAX_DEBT_SERVICE_SHARE:.0%} of gross income",
              [f"{cid} {d / income[cid]:.0%}" for cid, d in debt.items() if d > MAX_DEBT_SERVICE_SHARE * income[cid]], len(debt))

    fails = []
    for l in t["loans"]:
        start, principal, out = date.fromisoformat(l["start_date"]), float(l["principal_zar"]), float(l["outstanding_zar"])
        term, r = LOAN_TERM_MONTHS[l["loan_type"]], float(l["interest_rate_pct"]) / 1200
        paid = (run_date.year - start.year) * 12 + (run_date.month - start.month)
        expected = principal * ((1 + r) ** term - (1 + r) ** paid) / ((1 + r) ** term - 1)
        if not since[l["client_id"]] <= start <= run_date:
            fails.append(f"{l['loan_id']} started {start}, client since {since[l['client_id']]}")
        elif abs(out - expected) > 0.01 * principal:
            fails.append(f"{l['loan_id']} outstanding R{out:,.0f}, schedule says R{expected:,.0f}")
    rep.check("realism", "loans start after joining; outstanding matches repayment schedule", fails, len(t["loans"]))

    repay = defaultdict(int)
    for x in txns:
        if x["merchant_category"] == "loan_repayment":
            repay[acct_client[x["account_id"]]] += 1
    rep.check("realism", "every client with a loan has monthly debit orders",
              [cid for cid in debt if repay[cid] < 1], len(debt))

    # ---------- realism: transactions ----------
    rep.check("realism", "transactions inside the history window and after the account opened",
              [x["txn_id"] for x in txns if not (max(history_start, date.fromisoformat(accounts[x["account_id"]]["opened_date"]))
                                                 <= tday(x) <= run_date)], len(txns))
    rep.check("realism", "sign matches direction; salaries and debit orders carry no card",
              [x["txn_id"] for x in txns if (x["amount_zar"] > 0) != (x["direction"] == "credit")
               or (x["channel"] in ("EFT", "Debit order") and x["card_id"] is not None)], len(txns))
    rep.check("realism", "timestamps carry the SAST offset (+02:00)",
              [x["txn_id"] for x in txns if not x["txn_ts"].endswith("+02:00")], len(txns))
    rep.check("realism", "fuel and groceries bought in person",
              [x["txn_id"] for x in txns if x["merchant_category"] in ("fuel", "groceries") and x["channel"] == "Online"], len(txns))

    pos = defaultdict(set)  # (client, day) -> countries with in-person purchases
    for x in txns:
        if x["channel"] == "POS":
            pos[(acct_client[x["account_id"]], tday(x))].add(x["country_code"])
    rep.check("realism", "no client shops in person in two countries on the same day",
              [f"{k[0]} on {k[1]}: {sorted(v)}" for k, v in pos.items() if len(v) > 1], len(pos))

    ONE_OFF = 40_000  # single purchases this big are one-offs, not monthly living costs
    spend = defaultdict(float)  # regular card spend, excluding loan repayments and one-offs
    for x in txns:
        if x["card_id"] and -ONE_OFF < x["amount_zar"] < 0:
            spend[acct_client[x["account_id"]]] += -x["amount_zar"]
    ratio = {cid: spend[cid] / months / income[cid] for cid in clients}
    normal = [cid for cid, c in clients.items() if story[c["client_id"]] == "none"]
    rep.check("realism", f"ordinary clients spend less than they earn (median {statistics.median(ratio[c] for c in normal):.0%} of income)",
              [f"{cid} spends {ratio[cid]:.0%} of income" for cid in normal if ratio[cid] > 1.0], len(normal))
    net = defaultdict(float)  # everything in minus everything out, excluding one-offs
    for x in txns:
        if not (x["card_id"] and x["amount_zar"] <= -ONE_OFF):  # one-offs are card purchases only
            net[acct_client[x["account_id"]]] += x["amount_zar"]
    net_months = {cid: net[cid] / income[cid] for cid in clients}  # in months of income
    tol = 0.15 + 0.3 / months  # short histories are noisier
    outliers = [f"{cid} net {net_months[cid] / months:+.0%} of income a month" for cid in normal
                if abs(net_months[cid] / months) > tol]
    # A statistical check: a few unusual clients are realistic, a pattern isn't
    rep.check("realism", f"ordinary clients' money in and out roughly balance (net within {tol:.0%} of income "
                         f"a month for 98%+; {len(outliers)} outliers)",
              outliers if len(outliers) > 0.02 * len(normal) else [], len(normal))
    corr = statistics.correlation([income[c] for c in normal], [spend[c] for c in normal])
    rep.check("realism", f"spend rises with income (correlation {corr:.2f}, need > 0.5)",
              [] if corr > 0.5 else [f"correlation {corr:.2f}"], len(normal))

    # ---------- signal: planted stories visible ----------
    stories = defaultdict(list)
    for c in clients.values():
        stories[story[c["client_id"]]].append(c["client_id"])
    n = len(clients)  # random sampling wobbles more in small banks: allow 4 standard errors
    rep.check("signal", "story shares match the plan within sampling error",
              [f"{s}: {len(stories[s]) / n:.1%} vs {p:.0%}" for s, p in STORY_SHARES.items()
               if abs(len(stories[s]) / n - p) > max(0.03, 4 * (p * (1 - p) / n) ** 0.5)], len(STORY_SHARES))

    main = {a["client_id"]: float(a["balance"]) for a in accounts.values() if a["product"] in ("Private Banking Account", "Signature Account")}
    idle = [main[c] / income[c] for c in stories["idle_cash"]]
    others = [main[c] / income[c] for c in clients if story[c] != "idle_cash"]
    rep.check("signal", f"idle_cash clients hold more cash than everyone else (min {min(idle, default=0):.1f} "
                        f"vs max {max(others, default=0):.1f} months of income)",
              [] if idle and min(idle) > max(others) else ["overlap"], len(idle))

    idle_net = sorted(net_months[c] for c in stories["idle_cash"])  # cash built up over the history
    normal_net = sorted(net_months[c] for c in normal)
    p90 = normal_net[int(0.9 * len(normal_net))] if normal_net else 0
    med = statistics.median(idle_net) if idle_net else 0
    rep.check("signal", f"idle_cash clients also build up cash in their flows (median {med:+.1f} vs ordinary 90th pct {p90:+.1f} months)",
              [] if med > p90 else ["no flow signal"], len(idle_net))

    q = max(30, 30 * months // 4)  # first and last quarter of the history
    fx = defaultdict(lambda: [0.0, 0.0])
    for x in txns:
        if x["merchant_category"] == "travel_foreign":
            age = (run_date - tday(x)).days
            if age > 30 * months - q:
                fx[acct_client[x["account_id"]]][0] += -x["amount_zar"]
            elif age <= q:
                fx[acct_client[x["account_id"]]][1] += -x["amount_zar"]
    growth = lambda group: sum(fx[c][1] for c in group) / max(1, sum(fx[c][0] for c in group))
    g, ctrl = growth(stories["forex_growth"]), growth([c for c in clients if story[c] != "forex_growth"])
    rep.check("signal", f"forex_growth clients' foreign spend grows ({g:.1f}x) while others stay flat ({ctrl:.1f}x)",
              [] if g > 2 and 0.6 < ctrl < 1.6 else [f"growth {g:.1f}x, control {ctrl:.1f}x"], len(stories["forex_growth"]))

    planted = [x for x in txns if x["txn_id"] in planted_ids]
    per_client = defaultdict(int)
    fails = []
    for x in planted:
        cid = acct_client[x["account_id"]]
        per_client[cid] += 1
        hour = int(x["txn_ts"][11:13])
        if (story[cid] != "anomaly" or hour > 5 or x["channel"] != "Online" or x["country_code"] == "ZA"
                or (run_date - tday(x)).days > 19 or not 45_000 <= -x["amount_zar"] <= 120_000
                or not x["card_id"] or -x["amount_zar"] > float(cards[x["card_id"]]["credit_limit_zar"])):
            fails.append(f"{x['txn_id']} breaks the anomaly definition")
    fails += [f"{cid} has {per_client[cid]} planted anomalies" for cid in stories["anomaly"] if per_client[cid] != 1]
    rep.check("signal", "one anomaly per anomaly client: foreign, online, 00:00-05:59, last 20 days, R45k-R120k, within limit",
              fails, len(stories["anomaly"]))

    # ---------- leak: no single column separates a planted story ----------
    is_anom = [x["txn_id"] in planted_ids for x in txns]
    n_anom = sum(is_anom)
    min_amt = min((-x["amount_zar"] for x in planted), default=0)
    features = {
        "hour before 06:00": lambda x: int(x["txn_ts"][11:13]) < 6,
        f"amount >= R{min_amt:,.0f}": lambda x: -x["amount_zar"] >= min_amt,
        **{f"country {c}": (lambda x, c=c: x["country_code"] == c) for c in {x["country_code"] for x in planted}},
        **{f"merchant {m}": (lambda x, m=m: x["merchant_name"] == m) for m in {x["merchant_name"] for x in planted}},
        **{f"category {k}": (lambda x, k=k: x["merchant_category"] == k) for k in {x["merchant_category"] for x in planted}},
    }
    fails = []
    for name, f in features.items():
        hits = [a for x, a in zip(txns, is_anom) if f(x)]
        precision = sum(hits) / len(hits) if hits else 0
        if sum(hits) == n_anom and precision >= 0.8:
            fails.append(f"'{name}' alone finds every anomaly at {precision:.0%} precision")
    rep.check("leak", "no single column finds all anomalies at 80%+ precision", fails, len(features))

    def avg_spend(group):
        return statistics.mean(spend[c] / months for c in group) if group else 0
    up = stories["upgrade_candidate"]
    peers = [c for c in clients if clients[c]["segment"] == "Signature" and 92_000 <= income[c] <= 140_000
             and story[c] == "none"]
    diff = avg_spend(up) / max(1, avg_spend(peers)) - 1
    rep.check("leak", f"upgrade candidates spend like Signature clients on similar income ({diff:+.0%})",
              [] if abs(diff) < 0.15 else [f"{diff:+.0%} difference"], len(up))


def check_determinism(run_date: str, rep: Report):
    """Same seed must give byte-identical output; a different seed must not."""
    here = Path(__file__).parent / "generate_bank_data.py"
    digests = []
    for seed in (42, 42, 7):
        with tempfile.TemporaryDirectory() as d:
            subprocess.run([sys.executable, str(here), "--clients", "200", "--months", "6", "--seed", str(seed),
                            "--run-date", run_date, "--out", d], check=True, capture_output=True)
            digests.append(b"".join(p.read_bytes() for p in sorted(Path(d).rglob("*.*"))))
    fails = []
    if digests[0] != digests[1]:
        fails.append("seed 42 gave different data on two runs")
    if digests[0] == digests[2]:
        fails.append("seed 7 gave the same data as seed 42")
    rep.check("integrity", "same seed = identical bank, different seed = different bank", fails, 2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="out")
    p.add_argument("--run-date", required=True)
    p.add_argument("--months", type=int, default=12, help="must match the generator run")
    a = p.parse_args()
    rep = Report()
    if a.months < 3:
        p.error("--months must be at least 3")
    story, planted_ids = load_truth(Path(a.out) / "ground_truth", a.run_date)
    run_checks(load(Path(a.out) / "bronze", a.run_date), story, planted_ids, date.fromisoformat(a.run_date), a.months, rep)
    check_determinism(a.run_date, rep)
    passed = sum(rep.results)
    print(f"\n{passed}/{len(rep.results)} checks passed")
    sys.exit(0 if passed == len(rep.results) else 1)

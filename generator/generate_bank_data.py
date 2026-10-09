"""
RM Copilot - Phase 1 synthetic data generator.

Creates a small, fake private bank: relationship managers, clients, accounts,
cards, loans and card/EFT/debit-order transactions. Writes one file per table into
./out/bronze/<table>/<run_date>.<ext>, the shape Azure Data Factory will copy
into the Bronze layer of the data lake.

Principles:
- Deterministic: the same --seed and --run-date always produce the same bank.
  Names come from their own random stream, so installing Faker changes names only.
- Linked: every foreign key points at a row that exists (referential integrity).
- Realistic relationships: income drives segment, balances, credit limits, loan sizes
  and spending; dates run in order (born, joined aged 21+, then products); loans pass
  an affordability check and their balances follow a real repayment schedule.
- Planted stories: some clients get idle cash, rising forex spend, upgrade eligibility
  or one anomalous transaction. Planted signals are hidden among look-alikes (night-time
  online shopping, legitimate large purchases) so no single column gives them away.
  The answer key is written to out/ground_truth/, never into Bronze: the lake must not
  contain the answers the Copilot is meant to find.
- POPIA-safe: no real people, no ID numbers, reserved email domain, invalid phone prefix.

Known simplifications (fine for a demo, say so if asked):
- Account balances are point-in-time snapshots; they aren't rebuilt from transactions.
- Credit card spend posts to the transactional account; cards have no statements.
- Loan size uses today's income even for older loans.

Usage:
    pip install faker            # optional; built-in SA name lists are used without it
    python generate_bank_data.py --clients 2000 --months 12 --seed 42 --run-date 2026-10-07
    python validate_bank_data.py --months 12 --run-date 2026-10-07   # run after every change
"""

import argparse
import csv
import json
import random
import uuid
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

try:
    from faker import Faker  # type: ignore
    HAVE_FAKER = True
except ImportError:
    HAVE_FAKER = False

SAST = timezone(timedelta(hours=2))  # South African Standard Time, no daylight saving

FIRST_NAMES = ["Thabo", "Lerato", "Sipho", "Naledi", "Johan", "Anika", "Kagiso", "Zanele",
               "Pieter", "Ayesha", "Mandla", "Refilwe", "Tshepo", "Nomvula", "Ruan", "Priya",
               "Lwazi", "Karabo", "Dineo", "Themba", "Charlene", "Bongani", "Mpho", "Lindiwe"]
LAST_NAMES = ["Mokoena", "Nkosi", "Dlamini", "van der Merwe", "Naidoo", "Botha", "Khumalo",
              "Mahlangu", "Pillay", "Molefe", "Ndlovu", "Smith", "Mthembu", "Pretorius",
              "Sithole", "Govender", "Maseko", "Venter", "Zulu", "Kruger"]
CITIES = [("Johannesburg", "Gauteng"), ("Pretoria", "Gauteng"), ("Sandton", "Gauteng"),
          ("Cape Town", "Western Cape"), ("Stellenbosch", "Western Cape"),
          ("Durban", "KwaZulu-Natal"), ("Umhlanga", "KwaZulu-Natal"),
          ("Gqeberha", "Eastern Cape"), ("Bloemfontein", "Free State"), ("Mbombela", "Mpumalanga")]

# Local merchants by category: (merchant names, typical spend range in ZAR before scaling)
LOCAL_MERCHANTS = {
    "groceries": (["Woolworths Food", "Checkers", "Pick n Pay", "Spar"], (300, 3500)),
    "fuel": (["Shell", "Engen", "BP", "Sasol"], (600, 1800)),
    "restaurants": (["Tashas", "Ocean Basket", "Mugg & Bean", "Local Grill"], (250, 2500)),
    "retail": (["Takealot", "Mr Price Home", "Incredible Connection", "Zara"], (400, 9000)),
    "health": (["Dis-Chem", "Clicks"], (150, 1500)),
    "travel_local": (["FlySafair", "Airlink", "Protea Hotels"], (1500, 12000)),
}
ONLINE_CATEGORIES = {"retail", "travel_local"}  # fuel and groceries are bought in person
DAILY_TXN_COUNT = ([0, 1, 2, 3], [25, 40, 25, 10])

# Foreign merchants: (name, country, channel, category). The electronics store is used by
# ordinary clients too, so the planted anomaly hides among normal foreign purchases.
FOREIGN_MERCHANTS = [("Heathrow Duty Free", "GB", "POS", "travel_foreign"),
                     ("Booking.com", "NL", "Online", "travel_foreign"),
                     ("Emirates", "AE", "Online", "travel_foreign"),
                     ("Galeries Lafayette", "FR", "POS", "travel_foreign"),
                     ("Apple Store London", "GB", "POS", "travel_foreign"),
                     ("Uber Dubai", "AE", "POS", "travel_foreign")]
FOREIGN_ONLINE_STORE = ("Global Electronics Online", "HK", "Online", "retail_foreign")
BIG_PURCHASES = [("Incredible Connection", "retail", "ZA", "POS"), ("Emirates", "travel_foreign", "AE", "Online"),
                 ("Coricraft", "retail", "ZA", "POS"), ("American Swiss", "retail", "ZA", "POS"),
                 ("Global Electronics Online", "retail_foreign", "HK", "Online")]

SEGMENTS = {
    # segment: (monthly income range ZAR, share of clients)
    "Private Banking": ((58_000, 91_900), 0.65),
    "Signature": ((92_000, 260_000), 0.35),
}
PRIME_RATE = 10.75  # prime as at the run date (SARB hike of 23 Sep 2026); the pipeline reads it from the rates table

# Lending norms (Rule 2: loans follow income). Multiples are of ANNUAL income.
LOANS = [
    # type,            chance, principal x annual income, rate margin vs prime, term (months)
    ("Home loan",       0.6,   (2.0, 3.5),                (-1.0, 0.5),          240),
    ("Vehicle finance", 0.5,   (0.3, 0.9),                (0.0, 2.5),           72),
]
MAX_DEBT_SERVICE_SHARE = 0.40  # banks won't lend if instalments exceed ~40% of gross income

# TFSA annual contribution limits by tax year (year the tax year starts, 1 March)
TFSA_ANNUAL_LIMITS = {**{y: 30_000 for y in (2015, 2016)}, **{y: 33_000 for y in (2017, 2018, 2019)},
                      **{y: 36_000 for y in range(2020, 2026)}, 2026: 46_000}
TFSA_LIFETIME = 500_000


def _expected_base_monthly_spend() -> float:
    counts, weights = DAILY_TXN_COUNT
    per_day = sum(c * w for c, w in zip(counts, weights)) / sum(weights)
    avg_amount = sum((lo + hi) / 2 for _, (lo, hi) in LOCAL_MERCHANTS.values()) / len(LOCAL_MERCHANTS)
    return per_day * avg_amount * 30.4


BASE_MONTHLY_SPEND = _expected_base_monthly_spend()


def rand_date(rng, start: date, end: date) -> date:
    return start + timedelta(days=rng.randint(0, (end - start).days))


def add_years(d: date, years: int) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # 29 February
        return d.replace(year=d.year + years, day=28)


class NameSource:
    """Names use their own random stream, so Faker on or off never shifts any other value."""
    def __init__(self, seed: int):
        self.rng = random.Random(seed * 7919 + 1)
        self.fake = None
        if HAVE_FAKER:
            self.fake = Faker("en_ZA")
            self.fake.seed_instance(seed)

    def person(self):
        if self.fake:
            return self.fake.first_name(), self.fake.last_name()
        return self.rng.choice(FIRST_NAMES), self.rng.choice(LAST_NAMES)


def make_id(prefix: str, rng: random.Random, length: int = 10) -> str:
    # Stable, readable surrogate keys driven by the seeded RNG (uuid4 would break determinism).
    # Transactions use 16 hex characters: with ~900,000 of them, 10 characters can collide.
    return f"{prefix}-{uuid.UUID(int=rng.getrandbits(128)).hex[:length]}"


def instalment(principal: float, rate_pct: float, months: int) -> float:
    r = rate_pct / 100 / 12
    return principal * r / (1 - (1 + r) ** -months)


def outstanding_after(principal: float, rate_pct: float, months: int, paid: int) -> float:
    """Balance left on an amortising loan after `paid` monthly instalments."""
    r = rate_pct / 100 / 12
    return principal * ((1 + r) ** months - (1 + r) ** paid) / ((1 + r) ** months - 1)


def months_between(a: date, b: date) -> int:
    return (b.year - a.year) * 12 + (b.month - a.month)


def tfsa_balance(rng: random.Random, opened: date, run_date: date) -> float:
    """Contribute part of each year's allowance since opening, then add modest growth."""
    first = opened.year if opened.month >= 3 else opened.year - 1
    last = run_date.year if run_date.month >= 3 else run_date.year - 1
    latest = TFSA_ANNUAL_LIMITS[max(TFSA_ANNUAL_LIMITS)]
    contributed = 0.0
    for year in range(first, last + 1):
        contributed += TFSA_ANNUAL_LIMITS.get(year, latest) * rng.uniform(0.3, 1.0)
    contributed = min(contributed, TFSA_LIFETIME)
    years_open = max(0.0, (run_date - opened).days / 365.25)
    return contributed * (1 + rng.uniform(0.03, 0.08) * years_open / 2)  # rough average growth


def txn(rng, account_id, card_id, day, hour, amount, merchant, category, country, channel):
    ts = datetime(day.year, day.month, day.day, hour, rng.randint(0, 59), rng.randint(0, 59), tzinfo=SAST)
    return {"txn_id": make_id("TX", rng, 16), "account_id": account_id, "card_id": card_id,
            "txn_ts": ts.isoformat(), "amount_zar": round(amount, 2),
            "direction": "credit" if amount > 0 else "debit",
            "merchant_name": merchant, "merchant_category": category,
            "country_code": country, "channel": channel}


def generate(n_clients: int, months: int, seed: int, run_date: date):
    rng = random.Random(seed)
    names = NameSource(seed)
    start = run_date - timedelta(days=30 * months)  # first day of transaction history

    rms = []
    for i in range(max(3, n_clients // 150)):
        first, last = names.person()
        rms.append({"rm_id": f"RM-{i + 1:03d}", "rm_name": f"{first} {last}",
                    "branch": rng.choice(["Sandton", "Rosebank", "Cape Town", "Umhlanga"])})

    clients, accounts, cards, loans, txns = [], [], [], [], []
    stories, planted = [], []  # ground truth: kept out of the Bronze tables

    for _ in range(n_clients):
        segment = "Private Banking" if rng.random() < SEGMENTS["Private Banking"][1] else "Signature"
        lo, hi = SEGMENTS[segment][0]
        income = int(round(rng.uniform(lo, hi), -2))
        first, last = names.person()
        city, province = rng.choice(CITIES)
        client_id = make_id("CL", rng)

        # Planted stories: the answer key goes to a separate ground-truth file
        story = rng.choices(
            ["none", "idle_cash", "forex_growth", "upgrade_candidate", "anomaly"],
            weights=[63, 12, 12, 10, 3])[0]
        if story == "upgrade_candidate":
            segment, income = "Private Banking", int(round(rng.uniform(92_000, 140_000), -2))

        # Dates in order: born, then joined aged 21+ before the history starts, then products
        joined_hi = start - timedelta(days=1)
        dob = rand_date(rng, date(1960, 1, 1), min(date(1996, 12, 31), add_years(joined_hi, -22)))
        joined = rand_date(rng, max(date(2008, 1, 1), add_years(dob, 21)), joined_hi)

        clients.append({
            "client_id": client_id,
            "first_name": first,
            "last_name": last,
            "date_of_birth": dob.isoformat(),
            # client_id in the address keeps every email unique (masking joins rely on it)
            "email": f"{first}.{last}".lower().replace(" ", "") + f".{client_id[3:]}@example.com",
            # "00" is not a valid SA prefix, so a generated number can never reach a real phone
            "mobile": f"+27 00 {rng.randint(100, 999)} {rng.randint(1000, 9999)}",
            "city": city,
            "province": province,
            "segment": segment,
            "monthly_income_zar": income,
            "risk_profile": rng.choices(["Conservative", "Moderate", "Aggressive"], [30, 50, 20])[0],
            "risk_profile_date": rand_date(rng, max(joined, date(2022, 1, 1)), run_date).isoformat(),
            "rm_id": rng.choice(rms)["rm_id"],
            "client_since": joined.isoformat(),
        })
        stories.append({"client_id": client_id, "story": story})

        # Accounts: every client has a transactional account; others are probabilistic
        txn_acct = make_id("AC", rng)
        balance = income * rng.uniform(0.3, 1.5)
        if story == "idle_cash":
            balance = income * rng.uniform(6, 12)  # several months of income sitting idle
        accounts.append({"account_id": txn_acct, "client_id": client_id,
                         "product": f"{segment} Account", "currency": "ZAR",
                         "opened_date": joined.isoformat(), "balance": round(balance, 2)})
        if rng.random() < 0.55:
            opened = rand_date(rng, max(joined, date(2015, 3, 1)), run_date - timedelta(days=30))
            accounts.append({"account_id": make_id("AC", rng), "client_id": client_id,
                             "product": "Tax-Free Savings", "currency": "ZAR",
                             "opened_date": opened.isoformat(),
                             "balance": round(tfsa_balance(rng, opened, run_date), 2)})
        if segment == "Signature" or rng.random() < 0.25:
            accounts.append({"account_id": make_id("AC", rng), "client_id": client_id,
                             "product": "Optimum Offshore", "currency": "USD",
                             "opened_date": rand_date(rng, max(joined, date(2018, 1, 1)), run_date).isoformat(),
                             "balance": round(income * rng.uniform(0.05, 0.5), 2)})  # USD, sized to income

        # Cards hang off the transactional account
        client_cards = []
        for card_type, limit_mult in [("Debit", 0), ("Platinum Credit", 2.5)]:
            card = {"card_id": make_id("CD", rng), "account_id": txn_acct, "card_type": card_type,
                    "credit_limit_zar": int(round(income * limit_mult, -3)) if limit_mult else None,
                    "last4": f"{rng.randint(0, 9999):04d}"}
            cards.append(card)
            client_cards.append(card)

        # Loans (Rule 2): size follows income, the bank checks affordability, and the
        # outstanding balance follows a real repayment schedule from the start date
        monthly_debt, client_loans = 0.0, []
        for loan_type, chance, multiple, margin, term in LOANS:
            if rng.random() >= chance:
                continue
            principal = int(round(income * 12 * rng.uniform(*multiple), -3))
            rate = round(PRIME_RATE + rng.uniform(*margin), 2)
            start_lo = max(joined, run_date - timedelta(days=30 * (term - 12)))  # loan still running
            start_day = rand_date(rng, start_lo, run_date - timedelta(days=30))
            pay = instalment(principal, rate, term)
            if monthly_debt + pay > MAX_DEBT_SERVICE_SHARE * income:
                continue  # unaffordable: a real bank would decline it
            monthly_debt += pay
            paid = months_between(start_day, run_date)
            loan = {"loan_id": make_id("LN", rng), "client_id": client_id,
                    "loan_type": loan_type, "principal_zar": principal,
                    "outstanding_zar": round(outstanding_after(principal, rate, term, paid), 2),
                    "interest_rate_pct": rate, "start_date": start_day.isoformat()}
            loans.append(loan)
            client_loans.append((loan, start_day, pay))

        # Spending (Rule 2): a monthly budget of 45-65% of what's left after loan instalments,
        # so spend follows income instead of segment
        budget = (income - monthly_debt) * rng.uniform(0.45, 0.65)
        scale = budget / BASE_MONTHLY_SPEND
        # Most of what's left is moved to savings each month. idle_cash clients don't do this,
        # which is exactly how their cash piles up.

        # Transactions
        debit_card, credit_card = client_cards
        client_txns, abroad_days = [], set()
        day = start
        while day <= run_date:
            if day.day == 25:  # salary
                client_txns.append(txn(rng, txn_acct, None, day, 9, income, "Salary - Employer",
                                       "income", "ZA", "EFT"))
            if day.day == 26 and story != "idle_cash":  # monthly transfer to savings and investments
                debt_now = sum(pay for _, loan_start, pay in client_loans if day > loan_start)  # only loans already running
                surplus = income - debt_now - budget
                client_txns.append(txn(rng, txn_acct, None, day, 10, -surplus * rng.uniform(0.7, 0.9),  # keep some headroom for travel
                                       "Transfer to investments", "savings_transfer", "ZA", "Transfer"))
            if day.day == 1:  # loan debit orders
                for loan, loan_start, pay in client_loans:
                    if day > loan_start:
                        client_txns.append(txn(rng, txn_acct, None, day, 6, -pay, f"{loan['loan_type']} instalment",
                                               "loan_repayment", "ZA", "Debit order"))
            # Forex: base chance, rising over time for forex_growth clients
            progress = (day - start).days / max(1, (run_date - start).days)
            fx_chance = 0.02 + (0.20 * progress if story == "forex_growth" else 0)
            abroad = False
            if rng.random() < fx_chance:
                merchant, country, channel, category = rng.choice(FOREIGN_MERCHANTS)
                abroad = channel == "POS"  # in person abroad means no SA card-present spend today
                if abroad:
                    abroad_days.add(day)
                client_txns.append(txn(rng, txn_acct, credit_card["card_id"], day, rng.randint(8, 22),
                                       -rng.uniform(1_500, 25_000) * scale, merchant, category, country, channel))
            if rng.random() < 0.01:  # ordinary clients shop at the foreign online store too
                merchant, country, channel, category = FOREIGN_ONLINE_STORE
                client_txns.append(txn(rng, txn_acct, credit_card["card_id"], day, rng.randint(0, 23),
                                       -rng.uniform(2_000, 15_000) * scale, merchant, category, country, channel))
            for _ in range(rng.choices(*DAILY_TXN_COUNT)[0]):
                cat = rng.choice(list(LOCAL_MERCHANTS))
                merchants, (lo_amt, hi_amt) = LOCAL_MERCHANTS[cat]
                online = cat in ONLINE_CATEGORIES and rng.random() < 0.6
                if abroad and not online:
                    continue
                hour = rng.randint(0, 5) if online and rng.random() < 0.05 else rng.randint(7, 21)  # some night shopping
                client_txns.append(txn(rng, txn_acct, rng.choice(client_cards)["card_id"], day, hour,
                                       -rng.uniform(lo_amt, hi_amt) * scale, rng.choice(merchants), cat, "ZA",
                                       "Online" if online else "POS"))
            day += timedelta(days=1)

        if story != "anomaly" and rng.random() < 0.06:  # legitimate big purchase: a look-alike for the anomaly
            merchant, category, country, channel = rng.choice(BIG_PURCHASES)
            when = rand_date(rng, start, run_date)
            while channel == "POS" and when in abroad_days:  # can't shop in person at home while abroad
                when = rand_date(rng, start, run_date)
            client_txns.append(txn(rng, txn_acct, credit_card["card_id"], when,
                                   rng.randint(8, 20), -rng.uniform(40_000, min(120_000, 0.9 * 2.5 * income)),
                                   merchant, category, country, channel))

        if story == "anomaly":  # large foreign online spend at night, unlike this client's history
            merchant, country, channel, category = FOREIGN_ONLINE_STORE
            client_txns.append(txn(rng, txn_acct, credit_card["card_id"],
                                   rand_date(rng, run_date - timedelta(days=19), run_date), rng.randint(0, 4),
                                   -rng.uniform(45_000, min(120_000, 0.9 * 2.5 * income)),
                                   merchant, category, country, channel))
            planted.append({"txn_id": client_txns[-1]["txn_id"], "client_id": client_id, "label": "anomaly"})

        client_txns.sort(key=lambda t: t["txn_ts"])  # one account's history in time order
        txns.extend(client_txns)

    bronze = {"relationship_managers": rms, "clients": clients, "accounts": accounts,
              "cards": cards, "loans": loans, "transactions": txns}
    ground_truth = {"client_stories": stories, "planted_anomalies": planted}
    return bronze, ground_truth


def write(tables: dict, out_dir: Path, run_date: date, zone: str = "bronze"):
    for name, rows in tables.items():
        folder = out_dir / zone / name
        folder.mkdir(parents=True, exist_ok=True)
        if name == "transactions":  # high volume: newline-delimited JSON, like a system export
            path = folder / f"{run_date.isoformat()}.jsonl"
            with path.open("w", encoding="utf-8", newline="\n") as f:  # same bytes on Windows and Linux
                for r in rows:
                    f.write(json.dumps(r) + "\n")
        else:
            path = folder / f"{run_date.isoformat()}.csv"
            with path.open("w", encoding="utf-8", newline="") as f:
                w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                w.writeheader()
                w.writerows(rows)
        print(f"{name:24s} {len(rows):>9,} rows -> {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--clients", type=int, default=2000)
    p.add_argument("--months", type=int, default=12)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--run-date", required=True, help="YYYY-MM-DD; fixed so reruns are identical")
    p.add_argument("--out", default="out")
    a = p.parse_args()
    if a.months < 3:
        p.error("--months must be at least 3 so quarterly trends are measurable")
    run = date.fromisoformat(a.run_date)
    print(f"Faker available: {HAVE_FAKER}")
    bronze, truth = generate(a.clients, a.months, a.seed, run)
    write(bronze, Path(a.out), run)                    # what Data Factory copies into the lake
    write(truth, Path(a.out), run, zone="ground_truth")  # answer key for testing; never uploaded

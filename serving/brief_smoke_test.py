"""
RM Copilot, Phase 5 Lab 14: the first AI briefs.

For each client_id you pass in:
  1. read the client's row from app.v_client_detail (and any flagged payments from app.v_client_anomalies)
  2. keep only the fields the brief needs (data minimisation: no surname, no exact age, no city)
  3. send them to an LLM through OpenRouter with a fixed set of instructions (the prompt, version PROMPT_VERSION)
  4. print the brief and save it in app.brief_log with the model, prompt version and token counts

Run from the repo root, with one or more client ids:
    python serving/brief_smoke_test.py CL-02fd9a3e72 CL-02e1f4b1a3

Needs in serving/.env:  OPENROUTER_API_KEY, OPENROUTER_MODEL  (plus SQL_SERVER, SQL_DATABASE from Lab 12)
"""

import json
import os
import sys
import time
from datetime import date, datetime
from decimal import Decimal

import requests
from dotenv import load_dotenv

from load_gold_to_sql import HERE, connect   # same sign-in as the loader, no second copy of that code

load_dotenv(HERE / ".env")
# Which LLM provider to call: any OpenAI-format API (DeepSeek, OpenRouter, Ollama). Set in serving/.env.
BASE_URL = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
API_KEY = os.getenv("LLM_API_KEY") or os.environ["OPENROUTER_API_KEY"]
MODEL = os.getenv("LLM_MODEL") or os.environ["OPENROUTER_MODEL"]
PROMPT_VERSION = "v7"

# ----------------------------------------------------------------------------- the prompt
# The system prompt is the AI's standing instructions. Changing it changes every brief,
# so it has a version number that is saved with each brief in app.brief_log.
SYSTEM_PROMPT = """You are an assistant to a relationship manager (RM) at a South African private bank.
You write a short call-preparation brief about ONE client, using ONLY the JSON data you are given.

Rules:
- Use only facts and numbers that appear in the data. Never invent products, amounts, dates or history,
  and never calculate new numbers (no totals, annual figures or ratios of your own).
- Money is in South African rand: write it like R106,605. offshore_balance_usd is in US dollars: write it like $12,500.
- "signals" lists why this client is on the RM's list today. Explain each one using its supporting numbers.
- If "possible_fraud" is present, the whole brief is about the fraud and nothing else: headline, why now,
  action and watch out. The RM must confirm whether the client made the payment, without accusing them.
  In a fraud brief, mention ONLY the flagged payment's own facts (amount, merchant, country,
  channel, date and time). Do not mention income, balances, card balance, limits, loans,
  debt ratios, products, investment, savings or credit.
- Affordability: if debt_to_annual_income is above 2.0, or card_utilisation_pct is 70 or more,
  do not suggest new credit (loans, overdrafts, higher card limits). Prefer savings, investment,
  offshore or fee-saving products. If card_utilisation_pct is 70 or more, mention the card balance
  in Watch out. card_balance_zar is what the client owes on credit cards today.
  Card balances are debt too: never describe a client as having no debt if card_balance_zar is above 0.
- If the data does not support a suggestion, say what the RM should ask instead.
- Plain, professional English. No greetings, no sign-off, no markdown headings.
- Never write field names from the data (like offshore_balance_usd); describe them in plain words.

Format, at most 160 words:
Headline: one sentence.
Why now: two or three bullets, each with a number from the data.
Suggested action: one or two sentences.
Watch out: one sentence (affordability, risk or data limits).
"""


# ----------------------------------------------------------------------------- read the client
def to_plain(value):
    """SQL values -> JSON-friendly values."""
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def read_client(cur, client_id: str) -> dict | None:
    cur.execute("SELECT * FROM app.v_client_detail WHERE client_id = ?", client_id)
    row = cur.fetchone()
    if row is None:
        return None
    detail = {col[0]: to_plain(v) for col, v in zip(cur.description, row)}

    cur.execute("SELECT txn_ts_utc, txn_date_sast, txn_hour_sast, amount_out_zar, merchant_name, "
                "country_code, channel FROM app.v_client_anomalies WHERE client_id = ? "
                "ORDER BY txn_ts_utc DESC", client_id)
    flagged = [{col[0]: to_plain(v) for col, v in zip(cur.description, r)} for r in cur.fetchall()]
    return {"detail": detail, "flagged": flagged}


def build_facts(client: dict) -> dict:
    """Keep only what the brief needs. Whatever is not in here can never reach the model."""
    d = client["detail"]
    facts = {
        "first_name": d["first_name"],
        "segment": d["segment"],
        "risk_profile": d["risk_profile"],
        "years_as_client": d["years_as_client"],
        "monthly_income_zar": d["monthly_income_zar"],
        "main_balance_zar": d["main_balance_zar"],
        "tfsa_balance_zar": d["tfsa_balance_zar"],
        "offshore_balance_usd": d["offshore_balance_usd"],
        "credit_limit_zar": d["credit_limit_zar"],
        "card_balance_zar": d["card_balance_zar"],
        "card_utilisation_pct": d["card_utilisation_pct"],
        "loans_outstanding_zar": d["loans_outstanding_zar"],
        "has_home_loan": bool(d["has_home_loan"]),
        "has_vehicle_finance": bool(d["has_vehicle_finance"]),
        "debt_to_annual_income": d["debt_to_annual_income"],
        "spend_last_90d_zar": d["spend_last_90d_zar"],
        "signals": {},
    }
    s = facts["signals"]
    if d["anomaly"]:
        s["possible_fraud"] = {"flagged_payments": client["flagged"]}
    if d["idle_cash"]:
        s["idle_cash"] = {"main_balance_in_months_of_income": d["idle_months_of_income"]}
    if d["upgrade_candidate"]:
        s["upgrade_candidate"] = {"current_segment": d["segment"],
                                  "monthly_income_zar": d["monthly_income_zar"]}
    if d["salary_increase"]:
        s["salary_increase"] = {"lowest_salary_zar": d["lowest_salary_zar"],
                                "highest_salary_zar": d["highest_salary_zar"],
                                "raise_pct": d["salary_raise_pct"]}
    if d["forex_growth"]:
        s["forex_growth"] = {"foreign_trips_first_3_months": d["forex_trips_first_3m"],
                             "foreign_trips_last_3_months": d["forex_trips_last_3m"]}
    return facts


# ----------------------------------------------------------------------------- ask the model
def ask_llm(facts: dict) -> dict:
    payload = {"model": MODEL,
               "temperature": 0.2,
               "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": json.dumps(facts, indent=2)}]}
    if "deepseek.com" in BASE_URL:
        payload["thinking"] = {"type": "disabled"}         # short rule-following task: no hidden reasoning to pay for

    for attempt in range(1, 4):                            # up to 3 tries
        response = requests.post(f"{BASE_URL}/chat/completions",
                                 headers={"Authorization": f"Bearer {API_KEY}"},
                                 json=payload, timeout=90)
        if response.status_code == 429 and attempt < 3:    # rate-limited: wait, then try again
            wait = 30 * attempt
            print(f"  rate-limited, waiting {wait}s (attempt {attempt}/3)...")
            time.sleep(wait)
            continue
        if response.status_code != 200:
            raise RuntimeError(f"LLM returned {response.status_code}: {response.text[:300]}")
        body = response.json()
        usage = body.get("usage") or {}
        return {"text": body["choices"][0]["message"]["content"].strip(),
                "model": body.get("model", MODEL),
                "input_tokens": usage.get("prompt_tokens"),
                "output_tokens": usage.get("completion_tokens")}


# ----------------------------------------------------------------------------- save
def save_brief(cur, client_id: str, brief: dict) -> int:
    cur.execute(
        "INSERT INTO app.brief_log (client_id, model, prompt_version, brief_text, input_tokens, output_tokens) "
        "OUTPUT INSERTED.brief_id VALUES (?, ?, ?, ?, ?, ?)",
        client_id, brief["model"][:100], PROMPT_VERSION, brief["text"],
        brief["input_tokens"], brief["output_tokens"])
    return cur.fetchone()[0]


# ----------------------------------------------------------------------------- main
def main(client_ids: list[str]) -> int:
    if not client_ids:
        print("Give one or more client ids, e.g. python serving/brief_smoke_test.py CL-02fd9a3e72")
        return 1

    conn = connect()
    cur = conn.cursor()
    failures = 0
    for client_id in client_ids:
        print("=" * 70)
        print(client_id)
        try:
            client = read_client(cur, client_id)
            if client is None:
                raise ValueError("not found in app.v_client_detail")
            facts = build_facts(client)
            print(f"signals sent: {', '.join(facts['signals']) or 'none'}")

            brief = ask_llm(facts)
            brief_id = save_brief(cur, client_id, brief)
            conn.commit()

            print(f"model: {brief['model']} | tokens in/out: {brief['input_tokens']}/{brief['output_tokens']} "
                  f"| saved as brief_id {brief_id}\n")
            print(brief["text"])
        except Exception as err:
            conn.rollback()
            failures += 1
            print(f"FAILED: {err}")

    cur.close()
    conn.close()
    print("=" * 70)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

# RM Copilot

An AI copilot for private banking relationship managers (RMs), built end to end on Azure.

Before a client meeting, an RM should not have to dig through twelve months of transactions. The copilot does it for them: a client 360 view, a pre-meeting brief, next-best-action suggestions and flags for unusual activity. For example: *"Salary up 22% since August. Good moment to discuss a retirement annuity."*

All data is synthetic. No real client information is used anywhere in this project.

## Status

| Phase | What it covers | Status |
| --- | --- | --- |
| 1. Data sources | Synthetic bank generator, realism checks, SQL story hunts | Done |
| 2. Ingestion | ADLS Gen2 lake, Azure Data Factory pipelines, infrastructure as code | In progress |
| 3. Processing | Bronze, Silver and Gold layers in Databricks | Planned |
| 4. Machine learning | Anomaly detection, next-best-action | Planned |
| 5. Serving | Azure SQL, Azure AI Search | Planned |
| 6. AI layer | Embeddings and meeting briefs with Azure OpenAI | Planned |
| 7. Application | Next.js front end, Node API, Power BI | Planned |
| 8. Security and operations | Identity, monitoring, cost control | Planned |

## Architecture

```
Generator (laptop)  ->  ADLS Gen2 landing  ->  Data Factory  ->  Bronze  ->  Databricks (Silver, Gold)
                                                                               |
                     RM app (Next.js)  <-  Node API  <-  Azure SQL + AI Search + Azure OpenAI
```

## Phase 1: the synthetic bank

`generator/generate_bank_data.py` builds a small, realistic private bank. The default run (seed 42, run date 2026-10-07) produces:

| Table | Rows |
| --- | --- |
| relationship_managers | 13 |
| clients | 2,000 |
| accounts | 4,098 |
| cards | 4,000 |
| loans | 1,628 |
| transactions (12 months) | 944,598 |

The same seed always produces byte-identical files, which `compare_runs.py` proves with SHA-256 fingerprints.

### Hidden stories and the answer key

The generator secretly gives some clients a "story", the kind of pattern an RM would want to know about. The answer key is written to `out/ground_truth/`, separate from the Bronze tables, so no query or model can see it. Only `score_answers.py` opens it.

Each story is hunted with plain SQL and scored for precision (of the clients flagged, how many were right) and recall (of the real ones, how many were found).

| Story | What it means for the RM | Precision | Recall |
| --- | --- | --- | --- |
| idle_cash | Too much money sitting in a transactional account | 100.0% | 100.0% |
| upgrade_candidate | Earns enough for a higher banking tier | 100.0% | 100.0% |
| forex_growth | Spending more and more overseas | 99.3% | 99.6% |
| anomaly | One suspicious card transaction | 100.0% | 100.0% |
| salary_increase | Recently got a raise | 100.0% | 100.0% |

### Realism checks

`validate_bank_data.py` runs 36 checks a real bank would never fail: no client joins as a child, no loan the client could not afford, every card belongs to a real account. It exits with code 1 on any failure, so it can block a bad change in CI. In Lab 3, deliberate bugs were planted in the generator to prove the checks catch them.

## Run it yourself

Requires Python 3. Nothing else to install: SQLite ships with Python.

```powershell
git clone https://github.com/Don-the-dev-ops/rm-copilot.git
cd rm-copilot/generator

python generate_bank_data.py --run-date 2026-10-07
python validate_bank_data.py --run-date 2026-10-07
python load_bank.py --run-date 2026-10-07

python run_query.py queries/hunt/salary_increase.sql --save answers/salary_increase.csv
python score_answers.py answers/salary_increase.csv --story salary_increase --run-date 2026-10-07
```

Useful options: `--seed` and `--clients` on the generator, `--show` on `run_query.py` for how many rows to print.

## Repository layout

```
generator/
  generate_bank_data.py   builds the synthetic bank
  validate_bank_data.py   36 realism checks
  compare_runs.py         proves two runs are identical
  load_bank.py            loads Bronze files into SQLite (bank.db)
  run_query.py            runs a .sql file against bank.db
  score_answers.py        marks a hunt against the answer key
  queries/                practice queries
  queries/hunt/           one SQL hunt per story
```

Generated data (`out/`, `bank.db`, `answers/`) is ignored by Git.

## Design principles

- **Synthetic, POPIA-safe data.** Realistic South African names, cities and merchants, none of them real clients.
- **Reproducible.** A fixed seed and run date give identical output every time.
- **The answer key never touches Bronze.** Models are judged on data they could not have peeked at.
- **Checks are independent of the generator.** The validator uses lending norms, not the generator's own settings, so it can catch the generator being wrong.

## Author

Mpho Habai, Software Developer and Technical Business Analyst, Johannesburg.

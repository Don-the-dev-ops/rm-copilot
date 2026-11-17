# RM Copilot

An AI copilot for private banking relationship managers (RMs), built end to end on Azure.

Before a client meeting, an RM should not have to dig through twelve months of transactions. The copilot does it for them: a client 360 view, a pre-meeting brief, next-best-action suggestions and flags for unusual activity. For example: *"Salary up 22% since August. Good moment to discuss a retirement annuity."*

All data is synthetic. No real client information is used anywhere in this project.

## Status

| Phase | What it covers | Status |
| --- | --- | --- |
| 1. Data sources | Synthetic bank generator, realism checks, SQL story hunts | Done |
| 2. Ingestion | ADLS Gen2 lake, Azure Data Factory, incremental loads, daily trigger, infrastructure as code | Done |
| 3. Processing | Bronze, Silver and Gold layers in Databricks | Planned |
| 4. Machine learning | Anomaly detection, next-best-action | Planned |
| 5. Serving | Azure SQL, Azure AI Search | Planned |
| 6. AI layer | Embeddings and meeting briefs with Azure OpenAI | Planned |
| 7. Application | Next.js front end, Node API, Power BI | Planned |
| 8. Security and operations | Identity, monitoring, cost control | Planned |

## Architecture

```
Generator (laptop) --AzCopy--> ADLS Gen2 landing --Data Factory--> Bronze --> Databricks (Silver, Gold)
                                                   (daily trigger)                 |
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

## Phase 2: ingestion into the data lake

Phase 2 moves the bank's daily extracts from the laptop into Azure and lands them, untouched, in an immutable Bronze layer. Every Azure resource is created by a script in `infra/`, and every Data Factory component is a JSON file in `adf/`, so the whole setup can be rebuilt from this repo.

### The lake

One ADLS Gen2 storage account (hierarchical namespace on, so folders are real) in South Africa North, with four containers:

| Container | Holds | Written by |
| --- | --- | --- |
| landing | Extracts as uploaded, one file per table per run date | AzCopy, from the laptop |
| bronze | Every load kept, never edited, one folder per load date | Data Factory |
| silver | Cleaned, typed, de-duplicated tables | Databricks (Phase 3) |
| gold | Business-ready tables such as the client 360 | Databricks (Phase 3) |

```
bronze/
  clients/ingest_date=2026-11-17/2026-10-10.csv
  transactions/ingest_date=2026-11-17/2026-10-10.jsonl
  ...
  _control/watermark.txt     where the last script-driven run ended
  _audit/ingest_log.csv      what each script-driven run copied, per table
```

The answer key in `out/ground_truth/` never leaves the laptop.

### The pipeline

`pl_ingest_bank` loops over the six tables in parallel and copies each one from landing to `bronze/<table>/ingest_date=<run date>/` as a binary copy, byte for byte. Data Factory signs in to the lake with its system-assigned managed identity, so no keys or connection strings exist anywhere.

| Building block | File | Role |
| --- | --- | --- |
| Linked service | `adf/linkedService/ls_adls_rmcopilot.json` | The lake's address, using the managed identity |
| Datasets | `adf/dataset/ds_landing_binary.json`, `ds_bronze_binary.json` | Source and target folders, with the table and load date as parameters |
| Pipeline | `adf/pipeline/pl_ingest_bank.json` | ForEach over the table list, one parameterised Copy activity inside |
| Trigger | `adf/trigger/tr_ingest_daily.json` | Runs the pipeline every 24 hours |

### Incremental loads

Each run only copies files that **landed since the previous run**. Azure stamps every file with a last-modified time when AzCopy uploads it, and the Copy activity filters landing files to a window (`windowStart` to `windowEnd`). Two safeguards keep each file to exactly one copy:

- AzCopy uploads with `--overwrite=ifSourceNewer`, so older extracts keep their original timestamp.
- Windows are chained: each one starts exactly where the previous one ended.

The daily **tumbling window trigger** supplies the windows: back to back, no gaps, no overlaps, with automatic retries and backfill of missed windows. Before the trigger existed, `infra/06_run_incremental.ps1` did the same job by hand, keeping a watermark file and a per-table audit log.

Tested with three successive extracts:

| Run | Window (UTC, 2026) | Files copied | Why |
| --- | --- | --- | --- |
| A | 11 Nov 17:32 to 14 Nov 14:46 | 0 | The only extract had already been loaded |
| B | 14 Nov 14:46 to 15:06 | 6 | A new extract landed inside the window |
| C | 14 Nov 15:06 to 15:09 | 0 | Nothing new since run B, so nothing copied twice |

For a later extract, the bytes AzCopy uploaded (267,185,229) matched the bytes Data Factory wrote to Bronze exactly.

### Build it yourself

Needs the Azure CLI, AzCopy and an Azure subscription.

```powershell
Copy-Item infra\00_config.example.ps1 infra\00_config.ps1   # then fill in your own values
.\infra\01_foundations.ps1      # resource group and monthly budget alert
.\infra\02_lake.ps1             # ADLS Gen2 account, four containers, your data role
.\infra\03_upload_landing.ps1   # upload the generator's Bronze files to landing
.\infra\04_data_factory.ps1     # Data Factory, its managed identity and its data role
.\infra\05_deploy_adf.ps1       # deploy everything in adf/ (triggers are left stopped)
```

Then start the trigger (`az rest --method post` on `.../triggers/tr_ingest_daily/start`). Every script is idempotent: running it twice gives the same result as running it once. `00_config.ps1` holds your real IDs and is ignored by Git.

### Known limitations

- Incremental loading works at **file** level. Each extract is a full snapshot, so de-duplicating rows across snapshots is the Silver layer's job in Phase 3.
- The audit log is written by the script, so trigger runs show in Data Factory Monitor but not in `ingest_log.csv`. Moving auditing into the pipeline, and failure alerts, are planned for Phase 8.

## Run the generator yourself

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
infra/
  00_config.example.ps1   settings template (copy to 00_config.ps1, which Git ignores)
  01_foundations.ps1      resource group and budget alert
  02_lake.ps1             ADLS Gen2 lake, containers, data role
  03_upload_landing.ps1   AzCopy upload of new or changed files to landing
  04_data_factory.ps1     Data Factory with a managed identity
  05_deploy_adf.ps1       deploys everything in adf/
  06_run_incremental.ps1  manual incremental run with watermark and audit log
adf/
  linkedService/          connection to the lake
  dataset/                landing and bronze folders
  pipeline/               pl_ingest_bank
  trigger/                tr_ingest_daily
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
- **Bronze is immutable.** Files land exactly as they arrived, one folder per load, so any later step can be re-run from raw data.
- **Infrastructure and pipelines as code.** Scripts and JSON in Git, no portal clicks, no secrets committed.
- **Managed identity, least privilege.** Data Factory gets one data role on one storage account and no keys.
- **Checks are independent of the generator.** The validator uses lending norms, not the generator's own settings, so it can catch the generator being wrong.

## Author

Mpho Habai, Software Developer and Technical Business Analyst, Johannesburg.
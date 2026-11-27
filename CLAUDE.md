# RM Copilot

A portfolio MVP for a fictional private bank, **Iris Bank**: an AI copilot that tells a
relationship manager (RM) who to call today, why, and what to say. Built by Mpho Habai
on Azure as a learning project. All data is synthetic.

## How to work with me

- I'm strong on Azure, SQL and Python; newer to front end. When you change front-end
  code, explain what you did and why in plain language, briefly.
- Small steps. Stop and show me before large or multi-file changes.
- **Never run `git commit`, `git push` or merge.** I review and commit myself.
- **Never read, print or edit `.env`, `.env.local` or `serving/.env`.** They hold secrets.
  Use the matching `.env.example` to see which settings exist.
- Don't run Azure CLI commands that create, change or delete resources without asking.

## Repo map

| Folder | What it is |
| --- | --- |
| `generator/` | Python synthetic bank generator (seed 42) and validator |
| `adf/`, `infra/` | Azure Data Factory pipeline JSON and PowerShell infra scripts |
| `databricks/` | Notebooks: Bronze, Silver, Gold (Delta tables) |
| `serving/` | Azure SQL schema and views (`serving/sql/`), Gold loader, brief smoke test (`brief_smoke_test.py`, prompt v6) |
| `web/` | **The app (Phase 7).** Next.js front end and API routes |
| `exports/`, `runs/`, `generator/out/` | Generated data, git-ignored. Never commit. |

## Data pipeline (for context)

Generator CSVs → Data Factory → ADLS Gen2 lake → Databricks Bronze → Silver → Gold
(`client_360`, `client_signals`, `anomaly_transactions`) → Azure SQL database `rmcopilot`
(schemas `stg`, `serve`, `app`) → the app reads the `app` views.

Signals (one per demo story): possible fraud (night-time anomalies), forex growth,
idle cash, salary increase, upgrade candidate. Each client also has card balance and
card utilisation. Rules were scored against a sealed answer key: four stories 100%
precision and recall, forex growth about 99%. The answer key (`generator/out/ground_truth`)
must never be read by the app.

## The app: `web/`

- Next.js 16 (App Router, TypeScript, Tailwind), Node 24 LTS. Read `web/AGENTS.md`
  before writing Next.js code; this version has changes from older Next.js.
- **Cache Components is enabled.** Data-loading server components need a `<Suspense>`
  boundary or `'use cache'`; follow the current Next.js docs rather than memory.
- UI components: **shadcn/ui only**, themed to the brand. No other UI libraries.
- One app, one deploy: pages plus API routes under `web/src/app/api/`. The API routes
  are the back end. The browser never sees the SQL token or the DeepSeek key.
- Until Lab 17, all data is mock data in **`web/src/mock/data.ts`** (typed). Keep it in
  that one file so it can be swapped for SQL queries later.
- Database (Lab 17 onward): Azure SQL with Entra-only auth via an access token
  (`@azure/identity` + `mssql`). The free tier auto-pauses; the first query can fail
  with error 40613 for up to a minute, so retry and show a "waking up" state.
- AI briefs (Lab 19): DeepSeek `deepseek-flash`, called only from an API route, prompt
  v6 ported from `serving/brief_smoke_test.py`, every brief logged to `app.brief_log`,
  one brief per client per day reused.
- Hosting (Lab 20): Azure App Service (Linux, Node 24), managed identity to SQL.

## Screens

`/` welcome · `/rm` choose RM (one featured, Thandi Mokoena) · `/today` who to call,
ranked risk first · `/clients` full book · `/clients/[id]` client page with Generate
brief · `/how-it-works` pipeline for technical viewers. Plus loading, waking-up,
empty and error states.

## Design

- Brand: Iris Bank. Logo `web/public/iris-bank-logo.jpg` (light background). Navy and
  the logo's orange are the only brand colours. The UI is flat; the logo's gloss
  doesn't carry over.
- Feel: calm and credible, like a well-designed private bank statement. Numbers are
  the hero: tabular figures, right-aligned amounts, rand as `R104,221.86`. Dense
  where the RM works, spacious where a visitor lands.
- Always label the app as synthetic data.
- Avoid: gradients, gradient text, glows, glassmorphism; uppercase eyebrow above a
  giant headline as the default hero; three identical 01/02/03 feature cards; pill
  badges on everything; dark full-width CTA bands; emoji or icon-in-a-circle
  decoration; stacked soft-shadow cards; left-border accent cards; filler copy.
- Accessibility: real buttons and links, 4.5:1 contrast, visible focus, works at
  phone width.

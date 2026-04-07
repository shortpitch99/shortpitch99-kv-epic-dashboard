# KV Epic Dashboard

Streamlit dashboard for Epic milestone visibility from two GUS Salesforce reports:

- `00OEE000002tild2AA` (SCRT2 milestones)
- `00OEE000002tu8T2AQ` (VegamDB milestones)

## What this project does

- Pulls both milestone reports from Salesforce Analytics API.
- Shows two tabs: **SCRT2 milestones** and **VegamDB milestones**.
- Displays milestone, team, epic(work), health(status), epic health comment, `% complete`, and remaining work items.
- Saves a combined week-over-week snapshot in `data/weekly_reports/`.
- Lets you select historical weekly snapshots from the left sidebar.

## Setup

1. Create and activate your Python environment.
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Authenticate one of these ways:
   - Set environment variables:
     - `SF_INSTANCE_URL` (for example `https://gus.lightning.force.com`)
     - `SF_ACCESS_TOKEN`
   - Or QC-style fallback variables:
     - `SALESFORCE_SESSION_ID`
     - `SALESFORCE_INSTANCE` (for example `gus.lightning.force.com`)
   - Or place these in `KV/.env`

## Weekly workflow

```bash
./run_report.sh
./run_dashboard.sh
```

- `run_report.sh` fetches both milestone reports, creates metadata, generates LLM narrative, and saves a weekly artifact.
- `run_dashboard.sh` only renders saved artifacts; it does not call GUS directly.

## Quick start (QC-style)

Generate weekly report:

```bash
./run_report.sh
```

Generate from exported Excel instead of API (per tab):

```bash
./run_report.sh --scrt2-xlsx "/Users/rchowdhuri/Downloads/SCRT2 Milestones-2026-03-31-06-55-40.xlsx" --vegamdb-xlsx "/path/to/VegamDB Milestones.xlsx"
```

Auto-discover Excel files by calendar week folder:

```bash
# Put files in: data/xlsx/cw14/
# e.g. SCRT2 Milestones-....xlsx and VegamDB Milestones-....xlsx
./run_report.sh --week cw14
```

Filename matching is automatic:
- files with `scrt2` map to the SCRT2 tab
- files with `vegamdb` (or `vega`) map to the VegamDB tab
- if one file is missing, that tab falls back to GUS API

Launch dashboard:

```bash
./run_dashboard.sh
```

`run_report.sh`:
- creates `.venv` and installs dependencies
- loads `KV/.env` if present
- falls back to `/Users/rchowdhuri/QC/.env` for Salesforce auth only (LLM keys are never read from QC)
- calls `run_report.py` to save `data/weekly_reports/weekly_report_<week>_<timestamp>.json`
- accepts passthrough args such as `--scrt2-xlsx` and `--vegamdb-xlsx`
- supports `--week cwNN` and auto-reads `data/xlsx/cwNN/*.xlsx`

LLM narrative uses (set in `KV/.env`, your environment, or Streamlit Cloud secrets — not from QC):
- `LLM_GW_EXPRESS_KEY` (required for LLM narrative; fallback summary is used if missing)
- `OPENAI_USER_ID` (optional)

# CredResolve | Collections Analytics — Final Submission

**Prepared by:** Aditya Dwivedi  
**Submitted to:** CredResolve  
**Submission standard:** Decision-ready, reproducible, evidence-led analytics using the supplied data only.

## Executive conclusion

The supplied payment extracts support **17,534 canonical successful positive payment transactions**, **13,284 paying accounts** and **₹1,315,583,964.64 (₹131.56 crore)** in gross successful payment value. The available payment period is **1 January–8 August 2026**; August is partial. The stated **11% month-on-month improvement is NOT VERIFIABLE** as a sustained recovery-rate claim from these extracts. March's +11.03% is one month-on-month change in gross payment value, not proof of a sustained recovery-rate improvement.

The project recommends **not committing the full ₹10 crore on the present evidence**. Run a stratified, randomized 6–8 week targeting pilot, measure incremental net successful recovery against a holdout, include operating costs and customer safeguards, and release capital in stages only after pre-agreed unit-economics and confidence gates are met.

## GitHub repository reference

- **GitHub profile/account:** [https://github.com/Adityad2018](https://github.com/Adityad2018)
- **Suggested repository name:** `CredResolve-Collections-Analytics`
- **Repository URL:** Pending publication. No repository URL is claimed until the project is pushed and verified.
- **Publishing steps:** see `docs/GITHUB_PUBLISHING.md`.
- **Data protection:** the ZIP contains supplied raw extracts for the assignment handoff. Review the data owner's sharing permission before pushing any raw borrower, account, payment, contact, or operational records to a public or private GitHub repository. The `.gitignore` excludes raw extracts and local databases by default.

## Submission contents

- `reports/FINAL_HISTORICAL_ANALYTICS_REPORT.pdf` — full historical report, including scope, findings, limitations, investment decision and the explicit **10/10 deliverable-quality objective**.
- `reports/Executive_Memo.md` — executive decision memo (Markdown source; render and verify page count if a PDF memo is required).
- `dashboard/app.py` — Streamlit management dashboard.
- `notebooks/` — profiling, end-to-end analysis and experimental forecast/model-comparison walkthroughs.
- `sql/` — profiling and analytical SQL.
- `outputs/` — Golden Payments, monthly KPIs, exceptions, cleaning impact, identity, campaign, channel, portfolio and forecast outputs.
- `src/` — pipeline, curated-output rebuild, forecast experiments and validation scripts.
- `docs/architecture.mmd` — architecture diagram source.
- `docs/PRODUCTION_ANALYTICS_DESIGN.md` — production controls, contracts, keys, lineage, incremental loads, late events, backfills and monitoring.
- `docs/SUBMISSION_DELIVERABLES_CHECKLIST.md` — assignment-to-artifact mapping and explicit coverage status.
- `data/raw/` — supplied source extracts; preserve as immutable inputs.

## Reproduce and validate on macOS

Use Python 3.11 or later. From the project root:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python src/rebuild_curated_outputs.py
python src/validate_deliverables.py
streamlit run dashboard/app.py
```

Open notebooks with `jupyter lab` and run the analysis notebooks from top to bottom. Execute SQL using SQLite/DB Browser or the project's SQLite database.

**Important:** `src/run_full_project.py` is retained as a historical/legacy runner and contains superseded payment-reference deduplication logic. Do not use it to regenerate final Golden outputs. Use the revised `src/rebuild_curated_outputs.py` and then `src/validate_deliverables.py`.

## Evidence and analytical guardrails

- `payment_id` is the provisional transaction key, subject to processor confirmation. Payment references are exception flags, not transaction keys.
- Gross successful payment value is not incremental recovery, net recovery, profit or ROI.
- Account-level analysis uses account identity; unresolved borrower and agent identity exceptions are retained, not force-matched.
- Call, SMS, WhatsApp, field, campaign and PTP event links do not support causal conversion claims or reliable agent/campaign rankings.
- Historical eligible-balance denominators, channel/vendor costs and payment-to-interaction attribution are not supplied; actual recovery rate, cost per rupee, causal channel lift and investment ROI cannot be verified.
- August 2026 is partial through 8 August. Do not compare it with full months as if complete.
- Forecasts are experimental gross-payment scenarios, not actuals, incremental recovery or a committed budget.

## caution

This package is designed to achieve the highest defensible standard **within the available inputs**: traceable metrics, reproducible transformations, consistent definitions, clear decision recommendations and transparent limitationns and meaning the source data is complete. Missing months, costs, historical denominators and attribution keys are explicitly identified as data-owner dependencies; they are not fabricated to create artificial completeness.

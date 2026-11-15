# Assignment deliverables — submission checklist

This checklist follows the assignment's seven named deliverables and five analytical parts.

## Seven required deliverables
1. **SQL repository** — `sql/collections_analytics.sql`, `sql/phase1_profiling.sql`; reproducible cleaning, transformations, metrics and analytical queries.
2. **Analysis notebook** — `notebooks/01_data_profiling_identity_audit.ipynb`, `notebooks/02_full_analysis.ipynb`, `notebooks/03_adamw_six_month_forecast.ipynb`, `notebooks/04_adam_gru_lstm_comparison.ipynb`.
3. **Golden dataset / pipeline** — `outputs/golden_payments.csv`, `src/rebuild_curated_outputs.py`, `src/validate_deliverables.py`.
4. **Data quality report** — `outputs/data_quality_issue_register.csv`, `outputs/cleaning_impact_summary.csv`, `outputs/payment_exceptions.csv`, identity/campaign/timezone forensics outputs and `reports/Phase_1_Data_Quality_and_Identity_Audit.pdf`.
5. **Executive dashboard** — `dashboard/app.py`; one-screen executive command centre plus drill-down pages, including historical coverage and forecast comparison.
6. **Executive memo (maximum two pages)** — `reports/Executive_Memo.md`. Verify rendered PDF/page count before submission.
7. **Architecture diagram** — `docs/architecture.mmd`, plus `docs/PRODUCTION_ANALYTICS_DESIGN.md`.

## Five analytical parts in the brief
- **Part 1 — Golden Dataset:** source-of-truth decisions, entity resolution, deduplication, missingness, timestamp treatment, payment attribution, exclusions, assumptions and cleaning impact.
- **Part 2 — Data Forensics:** duplicate payments, attribution, timezone, vendor mapping, agent identity, portfolio mix and denominator risks.
- **Part 3 — Statistical Investigation:** mix/cohort/selection/survivorship/Simpson/attribution-window/time-series effects. Conclusions must be labelled Fact, Strong Evidence, Correlation or Hypothesis.
- **Part 4 — Counterfactual:** treatment/control, assumptions, confounders, identification and limitations; current campaign/interaction lineage is insufficient for a reliable causal estimate, so the documented experiment design is a proposed methodology.
- **Part 5 — Production Analytics Design:** Raw → Staging → Clean → Golden → Feature → Metrics → Dashboard; contracts, keys, lineage, incremental processing, late data, backfills, checks, monitoring and anomaly detection.

## Coverage caveat that must remain visible
The payment events supplied run from 1 January to 8 August 2026; August is partial. Other event sources also end around August 2026. The data does not provide 12 complete months of payment history. Do not invent missing historical months or present them as zero. The exact 12-month comparison window must be confirmed with the data owner and missing extracts requested.

## Forecast comparison
`src/forecast_model_comparison.py` compares MLP-Adam, GRU-Adam and LSTM-Adam against a naive 7-day mean baseline. The comparison is preliminary because the available history is short. Forecast values are gross payment scenarios, not incremental recovery or ROI.


## GitHub reference

- GitHub account: [Adityad2018](https://github.com/Adityad2018)
- Suggested repository: `CredResolve-Collections-Analytics`
- Publication status: pending user-created remote and push; no remote URL is represented as live.
- Publishing guide: `docs/GITHUB_PUBLISHING.md`.

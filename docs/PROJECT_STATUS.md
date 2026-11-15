# Project status — final technical correction

- Golden payment definition: payment_id; conflicting non-null account, amount, status or event-time groups are quarantined.
- `sql/collections_analytics.sql` now follows the revised payment_id policy; payment_reference is diagnostic only.
- `src/validate_deliverables.py` executes the SQL views and checks 17,534 rows, ₹1,315,583,964.64 gross, zero payment ID conflicts and eight observed monthly buckets.
- `notebooks/02_full_analysis.ipynb` is valid nbformat 4 and contains reproducible payment, identity, campaign and evidence-ledger analysis.
- Production design now documents keys, metric contracts, data lineage, incremental processing, late events, backfills, quality gates, monitoring and experiment controls.
- Remaining source-data limitations are not repaired by code: only Jan–Aug 2026 payment events (August partial), no historical eligible-balance denominator, missing costs, unstable identity joins and missing interaction-to-payment attribution.
- Dashboard syntax is checked, but browser runtime should be tested in an environment with requirements installed.

## Forecast extension (AdamW)
- Added `src/forecast_adamw.py` and `notebooks/03_adamw_six_month_forecast.ipynb`.
- Added dashboard page: `6-month forecast (AdamW)`.
- Forecast horizon: September 2026–February 2027, trained on daily Golden Payments through 8 August 2026.
- Validation: 28-day time-ordered holdout; AdamW is compared with a 7-day-mean naive baseline. In the current run AdamW does not beat the naive baseline, so this output is experimental and not suitable as a committed budget forecast.


## Adam / GRU / LSTM comparison
- Added `src/forecast_model_comparison.py`, notebook `04_adam_gru_lstm_comparison.ipynb`, comparison metrics and six-month model-level forecasts.
- All three neural models use Adam optimizer and a common 28-day lookback, calendar features, chronological 28-day holdout and recursive horizon. Naive 7-day mean baseline included.
- Added dashboard page `Model comparison (Adam / GRU / LSTM)`.
- Current single-holdout run: GRU lowest MAE and beats naive baseline; MLP-Adam and LSTM do not. Treat as preliminary pending rolling-origin tests and longer history.
- Added assignment-to-artifact checklist in `docs/SUBMISSION_DELIVERABLES_CHECKLIST.md`.

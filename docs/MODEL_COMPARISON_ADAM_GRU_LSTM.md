# Forecast model comparison: Adam, GRU and LSTM

## Terminology
Adam is an optimizer, not a forecasting architecture. This comparison therefore uses: (1) a feed-forward MLP optimized with Adam, (2) a GRU optimized with Adam, and (3) an LSTM optimized with Adam. A naive 7-day mean is included as a baseline. The earlier MLP+AdamW experiment remains separately available.

## Fair-comparison protocol
- Target: daily accepted, successful Golden Payment amount.
- Observed data: 2026-01-01 through 2026-08-08; 220 daily observations; August partial.
- Zero-payment days within the observed span are retained as zero. No missing months are invented.
- Inputs: previous 28 daily observations and calendar day-of-week/year Fourier features.
- Split: last 28 observed days held out chronologically; models trained only on preceding data.
- Recursive holdout forecast and recursive six-month forecast.
- Same Adam optimizer, Huber loss, learning rate 0.001, 180 epochs, and lookback for MLP, GRU and LSTM.
- Metrics: MAE, RMSE and WMAPE; naive 7-day mean baseline.

## Current single-holdout result
See `outputs/forecast_model_comparison_metrics.csv` for exact reproducible values. In the current run, GRU has the lowest holdout error among the neural models and also beats the 7-day mean baseline. MLP-Adam and LSTM do not beat that baseline. This is one 28-day holdout and is not enough to establish robust model superiority.

## Six-month output
`outputs/six_month_model_monthly_forecasts.csv` and `outputs/six_month_model_daily_forecasts.csv` contain model-level gross recovery projections for September 2026–February 2027. These are not incremental lift, net recovery, ROI or a committed budget forecast.

## Critical limitations
- Only about seven months of observed payments; no complete annual cycle.
- August is partial and there is no reliable 12-month historical payment panel in the supplied extracts.
- No exogenous portfolio inflow, eligible balance, DPD transitions, staffing, campaign, costs or macro drivers.
- Recursive six-month forecasts can drift.
- A single holdout can be sensitive to the selected dates and random initialization.

## Recommendation
Do not choose GRU for production solely from this run. Run multiple rolling-origin backtests, tune hyperparameters only within training windows, test stability across seeds, and compare against seasonal-naive/ETS or other transparent baselines once a complete 12–24 month history is obtained.

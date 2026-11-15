# Six-month recovery forecast — AdamW

## Objective
Provide an exploratory six-month projection of gross successful payment value, with explicit out-of-sample validation.

## Data
The model reads `outputs/golden_payments.csv`, retains accepted successful payments, aggregates amounts by calendar day, and fills days with no recorded payments as zero. Observed data runs from 2026-01-01 through 2026-08-08 (220 daily observations).

## Model
A compact feed-forward neural network uses the preceding 28 daily recovery values, day-of-week Fourier features, annual day-of-year Fourier features, and a bounded time index. The network uses ReLU hidden layers and a Softplus output to keep predictions non-negative. Optimization uses `torch.optim.AdamW` with learning rate 0.001 and weight decay 0.01.

## Validation
The final 28 observed days are held out in time order. The model is recursively evaluated against those days and compared with a simple baseline equal to the preceding seven-day mean. The recorded validation result is in `outputs/adamw_forecast_metadata.json`. In this run, AdamW MAE is approximately ₹7.77 lakh/day, versus approximately ₹6.07 lakh/day for the naive baseline; AdamW does not win.

## Forecast horizon
The model forecasts September 2026 through February 2027. Dates from 9–31 August are used as a recursive bridge and are not included in the displayed six full forecast months.

## Interpretation and limitations
- This is a forecast of gross recorded recovery, not incremental lift, net recovery, or ROI.
- The dataset contains fewer than eight months of observations and no full annual cycle; annual seasonality cannot be learned reliably.
- The model omits portfolio inflows, eligible balance, DPD transitions, staffing, campaign exposures, costs, macroeconomic drivers, and operational changes.
- Recursive forecasts accumulate error. The displayed monthly error bands are indicative MAE-based scenario bands, not calibrated 95% prediction intervals.
- Since the naive baseline outperforms AdamW on the holdout, the AdamW result must be labelled experimental and should not be used alone for budget commitments.
- Obtain a complete 12–24 month history and compare seasonal-naive, ETS/ARIMA, and regularized regression baselines before production use.

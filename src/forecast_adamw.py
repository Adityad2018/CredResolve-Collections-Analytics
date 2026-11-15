"""Experimental six-month daily-recovery forecast using a PyTorch MLP + AdamW.

Uses only accepted Golden Payments. Daily gaps are retained as zero-recovery days.
Forecast is an exploratory baseline, not a causal/investment ROI estimate.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
SEED = 42
LOOKBACK = 28
EPOCHS = 300
LR = 0.001
WEIGHT_DECAY = 0.01

torch.manual_seed(SEED)
np.random.seed(SEED)
torch.set_num_threads(1)

payments = pd.read_csv(OUT / "golden_payments.csv", parse_dates=["event_at"])
if "accepted_golden" in payments:
    payments = payments[payments["accepted_golden"].astype(str).str.lower().isin(["true", "1"])]
payments = payments[payments["payment_status"].astype(str).str.upper().eq("SUCCESS")]
payments["amount"] = pd.to_numeric(payments["amount"], errors="coerce").fillna(0)

start = payments.event_at.min().normalize()
last_observed = payments.event_at.max().normalize()
series = payments.groupby(payments.event_at.dt.normalize()).amount.sum()
idx = pd.date_range(start, last_observed, freq="D")
y = series.reindex(idx, fill_value=0).astype(float).to_numpy()
if len(y) <= LOOKBACK + 35:
    raise SystemExit("Insufficient daily history for the configured lag and holdout window.")

scale = max(float(np.mean(y)), 1.0)
y_scaled = y / scale

def features(history, target_date, origin_index):
    lag = np.asarray(history[-LOOKBACK:], dtype=float) / scale
    dow = target_date.dayofweek
    doy = target_date.dayofyear
    return np.r_[lag,
        np.sin(2*np.pi*dow/7), np.cos(2*np.pi*dow/7),
        np.sin(2*np.pi*doy/365.25), np.cos(2*np.pi*doy/365.25),
        min(origin_index / 365.25, 3.0)]

def make_train(values, dates):
    X, Y = [], []
    for t in range(LOOKBACK, len(values)):
        X.append(features(values[:t], dates[t], t))
        Y.append(values[t] / scale)
    return np.asarray(X, np.float32), np.asarray(Y, np.float32)

class RecoveryNet(nn.Module):
    def __init__(self, n_features):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 64), nn.ReLU(), nn.Dropout(0.10),
            nn.Linear(64, 32), nn.ReLU(), nn.Linear(32, 1), nn.Softplus()
        )
    def forward(self, x):
        return self.net(x).squeeze(-1)

def fit_model(values, dates, epochs=EPOCHS):
    X, Y = make_train(values, dates)
    xt = torch.tensor(X)
    yt = torch.tensor(Y)
    ds = TensorDataset(xt, yt)
    loader = DataLoader(ds, batch_size=min(32, len(ds)), shuffle=True)
    model = RecoveryNet(X.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.HuberLoss()
    for _ in range(epochs):
        model.train()
        for xb, yb in loader:
            optimizer.zero_grad()
            loss = loss_fn(model(xb), yb)
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
    return model

def recursive_forecast(model, history, dates, future_dates):
    vals = list(map(float, history))
    preds = []
    model.eval()
    for d in future_dates:
        x = torch.tensor(features(vals, d, len(vals)), dtype=torch.float32).unsqueeze(0)
        with torch.no_grad():
            pred = float(model(x).item()) * scale
        pred = max(pred, 0.0)
        preds.append(pred)
        vals.append(pred)
    return np.asarray(preds)

# Time-ordered 28-day holdout. Train only on data available before the holdout.
holdout_n = 28
train_y = y[:-holdout_n]
train_dates = idx[:-holdout_n]
holdout_dates = idx[-holdout_n:]
val_model = fit_model(train_y, train_dates, epochs=220)
val_pred = recursive_forecast(val_model, train_y, train_dates, holdout_dates)
actual = y[-holdout_n:]
mae = float(np.mean(np.abs(actual - val_pred)))
rmse = float(np.sqrt(np.mean((actual - val_pred) ** 2)))
wmape = float(np.sum(np.abs(actual - val_pred)) / max(np.sum(actual), 1.0) * 100)
naive = np.repeat(float(np.mean(train_y[-7:])), holdout_n)
naive_mae = float(np.mean(np.abs(actual - naive)))

# Refit on all observed daily data. Forecast full months Sep-2026 through Feb-2027.
final_model = fit_model(y, idx, epochs=EPOCHS)
bridge_dates = pd.date_range(last_observed + pd.Timedelta(days=1), "2026-08-31", freq="D")
future_dates = pd.date_range("2026-09-01", "2027-02-28", freq="D")
all_future_dates = bridge_dates.append(future_dates)
all_preds = recursive_forecast(final_model, y, idx, all_future_dates)
forecast = pd.DataFrame({"date": all_future_dates, "forecast_recovery_rupees": all_preds})
forecast = forecast[forecast.date.isin(future_dates)].copy()
forecast["month"] = forecast.date.dt.strftime("%Y-%m")
monthly = forecast.groupby("month", as_index=False).agg(
    forecast_recovery_rupees=("forecast_recovery_rupees", "sum"),
    forecast_days=("date", "nunique")
)
# Approximate model-error envelope: daily holdout MAE aggregated with sqrt(n).
# This is an indicative scenario band, not a calibrated 95% prediction interval.
monthly["indicative_error_band_rupees"] = 1.96 * mae * np.sqrt(monthly.forecast_days)
monthly["lower_scenario_rupees"] = (monthly.forecast_recovery_rupees - monthly.indicative_error_band_rupees).clip(lower=0)
monthly["upper_scenario_rupees"] = monthly.forecast_recovery_rupees + monthly.indicative_error_band_rupees
monthly["model"] = "MLP (PyTorch) · AdamW"
monthly["status"] = "Experimental forecast; not a commitment or causal estimate"
monthly.to_csv(OUT / "adamw_six_month_forecast.csv", index=False)
forecast.to_csv(OUT / "adamw_daily_forecast.csv", index=False)

metadata = {
    "model": "PyTorch feed-forward neural network optimized with AdamW",
    "optimizer": "AdamW", "learning_rate": LR, "weight_decay": WEIGHT_DECAY,
    "lookback_days": LOOKBACK, "epochs_final_fit": EPOCHS,
    "observed_start": str(idx.min().date()), "observed_end": str(idx.max().date()),
    "observed_daily_points": int(len(y)), "training_basis": "accepted successful positive Golden Payments",
    "holdout_days": holdout_n, "holdout_mae_rupees_per_day": mae,
    "holdout_rmse_rupees_per_day": rmse, "holdout_wmape_pct": wmape,
    "naive_7day_mean_holdout_mae_rupees_per_day": naive_mae,
    "beats_naive_baseline_on_holdout_mae": bool(mae < naive_mae),
    "forecast_months": monthly.month.tolist(),
    "limitations": [
        "Only 220 daily observations are available, ending 2026-08-08.",
        "August 2026 is partial; forecast starts with full September 2026.",
        "No full year of history is available to learn annual seasonality.",
        "No macroeconomic, portfolio inflow, staffing, campaign, or cost drivers are modelled.",
        "Recursive six-month neural forecasts can drift and should be treated as exploratory scenarios.",
        "Error bands are indicative and are not calibrated prediction intervals.",
        "Forecast is gross recorded recovery, not incremental recovery, net recovery, or ROI."
    ]
}
(OUT / "adamw_forecast_metadata.json").write_text(json.dumps(metadata, indent=2))
print(json.dumps({"metadata": metadata, "monthly_forecast": monthly.to_dict(orient="records")}, indent=2))

"""Fair comparison of MLP-Adam, GRU-Adam, and LSTM-Adam for collections recovery.

All models use the same daily Golden Payments series, 28-day lookback,
calendar features, chronological 28-day holdout, recursive forecast method,
loss, optimizer family, and six-month forecast horizon. A 7-day mean baseline
is included. With only ~220 observations, results are exploratory.
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
HOLDOUT = 28
EPOCHS = 180
LR = 0.001
BATCH_SIZE = 32

torch.set_num_threads(1)

def load_series():
    p = pd.read_csv(OUT / "golden_payments.csv", parse_dates=["event_at"])
    if "accepted_golden" in p:
        p = p[p.accepted_golden.astype(str).str.lower().isin(["true", "1"])]
    p = p[p.payment_status.astype(str).str.upper().eq("SUCCESS")].copy()
    p["amount"] = pd.to_numeric(p.amount, errors="coerce").fillna(0)
    start, end = p.event_at.min().normalize(), p.event_at.max().normalize()
    daily = p.groupby(p.event_at.dt.normalize()).amount.sum()
    dates = pd.date_range(start, end, freq="D")
    y = daily.reindex(dates, fill_value=0).astype(float).to_numpy()
    return dates, y

DATES, Y = load_series()
SCALE = max(float(np.mean(Y)), 1.0)

def day_features(d):
    dow, doy = d.dayofweek, d.dayofyear
    return np.array([np.sin(2*np.pi*dow/7), np.cos(2*np.pi*dow/7),
                     np.sin(2*np.pi*doy/365.25), np.cos(2*np.pi*doy/365.25)], dtype=np.float32)

def make_samples(values, dates):
    X_seq, X_flat, targets = [], [], []
    for t in range(LOOKBACK, len(values)):
        seq = []
        for j in range(t-LOOKBACK, t):
            seq.append(np.r_[values[j]/SCALE, day_features(dates[j])])
        cal = day_features(dates[t])
        X_seq.append(seq)
        X_flat.append(np.r_[np.asarray(values[t-LOOKBACK:t])/SCALE, cal, min(t/365.25, 3.0)])
        targets.append(values[t]/SCALE)
    return (np.asarray(X_seq, np.float32), np.asarray(X_flat, np.float32),
            np.asarray(targets, np.float32))

class MLP(nn.Module):
    def __init__(self, n):
        super().__init__(); self.net=nn.Sequential(nn.Linear(n,48),nn.ReLU(),nn.Linear(48,24),nn.ReLU(),nn.Linear(24,1),nn.Softplus())
    def forward(self,x): return self.net(x).squeeze(-1)

class RNNModel(nn.Module):
    def __init__(self, kind):
        super().__init__(); cell = nn.GRU if kind == "GRU" else nn.LSTM
        self.rnn=cell(input_size=5,hidden_size=24,num_layers=1,batch_first=True)
        self.head=nn.Sequential(nn.Linear(24+4,24),nn.ReLU(),nn.Linear(24,1),nn.Softplus())
    def forward(self, seq, cal):
        z=self.rnn(seq)[0][:,-1,:]
        return self.head(torch.cat([z,cal],dim=1)).squeeze(-1)

def train(kind, values, dates, epochs=EPOCHS):
    xs, xf, yt = make_samples(values, dates)
    torch.manual_seed(SEED)
    ds=TensorDataset(torch.tensor(xs),torch.tensor(xf),torch.tensor(yt))
    dl=DataLoader(ds,batch_size=min(BATCH_SIZE,len(ds)),shuffle=True)
    model=MLP(xf.shape[1]) if kind=="MLP-Adam" else RNNModel(kind)
    opt=torch.optim.Adam(model.parameters(),lr=LR)
    loss_fn=nn.HuberLoss()
    for _ in range(epochs):
        model.train()
        for seq,flat,target in dl:
            opt.zero_grad()
            if kind=="MLP-Adam": pred=model(flat)
            else: pred=model(seq,flat[:,-4:])
            loss=loss_fn(pred,target); loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(),1.0); opt.step()
    return model

def forecast(model, kind, history, history_dates, future_dates):
    vals=list(map(float,history)); dts=list(history_dates); preds=[]; model.eval()
    for d in future_dates:
        seq=np.asarray([np.r_[vals[-LOOKBACK+i]/SCALE,day_features(dts[-LOOKBACK+i])] for i in range(LOOKBACK)],np.float32)[None,:,:]
        cal=day_features(d)[None,:]
        with torch.no_grad():
            if kind=="MLP-Adam":
                flat=np.r_[np.asarray(vals[-LOOKBACK:])/SCALE,cal.ravel(),min(len(vals)/365.25,3.0)][None,:]
                z=float(model(torch.tensor(flat,dtype=torch.float32)).item())
            else: z=float(model(torch.tensor(seq),torch.tensor(cal)).item())
        value=max(0.0,z*SCALE); preds.append(value); vals.append(value); dts.append(d)
    return np.asarray(preds)

if len(Y) <= LOOKBACK + HOLDOUT:
    raise SystemExit("Not enough daily observations for 28-day lookback and holdout")
train_y, train_dates = Y[:-HOLDOUT], DATES[:-HOLDOUT]
test_y, test_dates = Y[-HOLDOUT:], DATES[-HOLDOUT:]
results=[]; fitted={}
for kind in ["MLP-Adam","GRU","LSTM"]:
    model=train(kind,train_y,train_dates,epochs=EPOCHS)
    pred=forecast(model,kind,train_y,train_dates,test_dates)
    mae=float(np.mean(np.abs(test_y-pred)))
    rmse=float(np.sqrt(np.mean((test_y-pred)**2)))
    wmape=float(np.sum(np.abs(test_y-pred))/max(np.sum(test_y),1.0)*100)
    results.append({"model":kind,"optimizer":"Adam","holdout_days":HOLDOUT,"MAE_rupees_per_day":mae,"RMSE_rupees_per_day":rmse,"WMAPE_pct":wmape})
    fitted[kind]=model
naive=np.repeat(float(np.mean(train_y[-7:])),HOLDOUT)
results.append({"model":"Naive 7-day mean","optimizer":"None","holdout_days":HOLDOUT,
                "MAE_rupees_per_day":float(np.mean(np.abs(test_y-naive))),
                "RMSE_rupees_per_day":float(np.sqrt(np.mean((test_y-naive)**2))),
                "WMAPE_pct":float(np.sum(np.abs(test_y-naive))/max(np.sum(test_y),1.0)*100)})
metrics=pd.DataFrame(results).sort_values("MAE_rupees_per_day")
metrics.to_csv(OUT/"forecast_model_comparison_metrics.csv",index=False)

# Fit on all observed data and recursively forecast six complete months.
bridge=pd.date_range(DATES[-1]+pd.Timedelta(days=1),"2026-08-31",freq="D")
future=pd.date_range("2026-09-01","2027-02-28",freq="D")
all_future=bridge.append(future)
daily_parts=[]
for kind in ["MLP-Adam","GRU","LSTM"]:
    final=train(kind,Y,DATES,epochs=EPOCHS)
    values=forecast(final,kind,Y,DATES,all_future)
    df=pd.DataFrame({"date":all_future,"forecast_recovery_rupees":values,"model":kind})
    daily_parts.append(df[df.date.isin(future)])
daily=pd.concat(daily_parts,ignore_index=True)
daily.to_csv(OUT/"six_month_model_daily_forecasts.csv",index=False)
monthly=daily.assign(month=daily.date.dt.strftime("%Y-%m")).groupby(["model","month"],as_index=False).agg(
    forecast_recovery_rupees=("forecast_recovery_rupees","sum"),forecast_days=("date","nunique"))
monthly.to_csv(OUT/"six_month_model_monthly_forecasts.csv",index=False)
meta={"observed_start":str(DATES.min().date()),"observed_end":str(DATES.max().date()),"daily_observations":len(Y),
      "history_note":"Observed payments only; missing months are not imputed as historical actuals.",
      "holdout":"Last 28 observed days; chronological split; recursive multi-step evaluation.",
      "lookback_days":LOOKBACK,"optimizer":"Adam for MLP, GRU, and LSTM","epochs":EPOCHS,
      "features":"28-day daily recovery sequence and calendar day-of-week/year Fourier features",
      "forecast_period":[str(future.min().date()),str(future.max().date())],
      "limitations":["Only about 7 months of daily payment history; no full annual seasonal cycle.","August is partial.","No exogenous portfolio, staffing, campaign, cost or macroeconomic predictors.","Recursive six-month forecasts are exploratory scenarios, not financial commitments.","Forecast is gross accepted payments, not incremental recovery or ROI."]}
(OUT/"forecast_model_comparison_metadata.json").write_text(json.dumps(meta,indent=2))
print("HOLDOUT MODEL COMPARISON\n",metrics.to_string(index=False))
print("\nSIX-MONTH FORECAST (₹ Cr)\n",monthly.assign(forecast_cr=monthly.forecast_recovery_rupees/1e7).pivot(index="month",columns="model",values="forecast_cr").round(2).to_string())
print("\nMETADATA\n",json.dumps(meta,indent=2))

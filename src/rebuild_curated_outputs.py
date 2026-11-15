from pathlib import Path
import pandas as pd, numpy as np, json
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'; OUT=ROOT/'outputs'
p=pd.read_csv(RAW/'payments.csv'); fields=[c for c in p.columns if c!='payment_id']
conf=[]
for pid,g in p.groupby('payment_id'):
 bad=[c for c in fields if g[c].dropna().nunique()>1]
 if bad: conf.append((pid,','.join(bad),len(g)))
if conf: raise ValueError(f'Conflicting payment_id groups found: {len(conf)}. Review manually; no automatic deduplication.')
c=p.groupby('payment_id',as_index=False,sort=False).agg({c:'first' for c in fields}); c['amount']=pd.to_numeric(c.amount,errors='coerce')
g=c[(c.payment_status.astype(str).str.upper()=='SUCCESS')&(c.amount>0)].copy();g['accepted_golden']=True;g.to_csv(OUT/'golden_payments.csv',index=False)
g['event_at']=pd.to_datetime(g.event_at,errors='coerce');g['month']=g.event_at.dt.to_period('M').astype(str)
m=g.groupby('month').agg(successful_recovery_amount=('amount','sum'),successful_payment_count=('payment_id','nunique'),unique_paying_accounts=('account_id','nunique')).reset_index();m['mom_recovery_change_pct']=m.successful_recovery_amount.pct_change()*100;m['recovery_per_account_rupees']=m.successful_recovery_amount/m.unique_paying_accounts;m.to_csv(OUT/'monthly_recovery_kpis.csv',index=False)
print(f'Golden payments: {len(g):,}; unique payment IDs: {g.payment_id.nunique():,}; gross recovery: ₹{g.amount.sum()/1e7:,.2f} Cr; paying accounts: {g.account_id.nunique():,}')

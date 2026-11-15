from pathlib import Path
import pandas as pd, numpy as np, sqlite3, json, warnings
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
warnings.filterwarnings('ignore')
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'; OUT=ROOT/'outputs'; VIZ=ROOT/'visualizations'; REP=ROOT/'reports'; DB=ROOT/'data/processed/collections.db'
for p in [OUT,VIZ,REP,DB.parent]: p.mkdir(parents=True,exist_ok=True)

def load(name): return pd.read_csv(RAW/f'{name}.csv')
def save(df,name): df.to_csv(OUT/f'{name}.csv',index=False)
def month(s): return pd.to_datetime(s,errors='coerce').dt.to_period('M').astype(str)
# Load all source tables and preserve raw inputs
files=sorted(RAW.glob('*.csv')); tables={f.stem:pd.read_csv(f) for f in files if f.stem!='data_dictionary'}
# SQLite raw layer
with sqlite3.connect(DB) as con:
    for n,d in tables.items(): d.to_sql('raw_'+n,con,if_exists='replace',index=False)
# Entity resolution: deterministic crosswalks only; conflicting mappings remain exceptions
accounts=tables['accounts'].copy(); borrowers=tables['borrowers'].copy(); agents=tables['agents'].copy()
account_borrower=accounts[['account_id','borrower_id']].drop_duplicates()
# Agent alias map via employee_code; detect collisions before choosing stable canonical id
ag=agents.copy(); ag['canonical_agent_id']=ag.groupby('employee_code')['agent_id'].transform('min')
agent_conf=ag.groupby('employee_code').agg(agent_ids=('agent_id','nunique'),names=('agent_name','nunique'),vendors=('vendor_id','nunique')).reset_index()
agent_conf['resolution_status']=np.where((agent_conf.agent_ids==1)&(agent_conf.names==1),'UNIQUE','REVIEW_REQUIRED')
save(agent_conf,'agent_entity_resolution')
# account borrower conflicts across event tables
rel=[]
for t in ['calls','call_attempts','call_dispositions','whatsapp_events','sms_events','field_visits','promises_to_pay','payments','complaints','account_status_history']:
 d=tables[t]
 if {'account_id','borrower_id'}.issubset(d.columns):
  z=d[['account_id','borrower_id']].drop_duplicates().merge(account_borrower,on='account_id',how='left',suffixes=('_event','_master'))
  z['source_table']=t; z['mismatch']=z.borrower_id_event.notna()&z.borrower_id_master.notna()&(z.borrower_id_event!=z.borrower_id_master)
  rel.append(z)
rel=pd.concat(rel,ignore_index=True); save(rel,'account_borrower_crosswalk_exceptions')
# Payment forensics: exclude non-success and reversed/pending; conservative dedupe by exact payment_reference, account and amount
pay=tables['payments'].copy(); pay['event_at']=pd.to_datetime(pay.event_at,errors='coerce'); pay['month']=month(pay.event_at)
pay['amount']=pd.to_numeric(pay.amount,errors='coerce')
pay['is_success']=pay.payment_status.astype(str).str.upper().eq('SUCCESS') & pay.amount.gt(0)
pay['reference_rows']=pay.groupby('payment_reference').payment_id.transform('size')
pay['reference_signature']=pay[['account_id','amount','payment_status']].astype(str).agg('|'.join,axis=1)
pay['reference_variants']=pay.groupby('payment_reference').reference_signature.transform('nunique')
pay['duplicate_reference']=pay.reference_rows.gt(1) & pay.payment_reference.notna()
pay['duplicate_exact']=pay.duplicated(['account_id','payment_reference','amount','payment_status'],keep='first')
pay['ambiguous_reference']=pay.duplicate_reference & pay.reference_variants.gt(1)
pay['accepted_golden']=pay.is_success & ~pay.ambiguous_reference & ~pay.duplicate_exact
pay['rejection_reason']=np.select([~pay.is_success,pay.ambiguous_reference,pay.duplicate_exact],['NOT_SUCCESS_OR_NONPOSITIVE','AMBIGUOUS_REPEATED_REFERENCE','EXACT_DUPLICATE_RETRY'],default='ACCEPTED')
save(pay,'payment_forensics_all_records'); save(pay.loc[~pay.accepted_golden],'payment_exceptions')
# Golden payments and account dimension
pg=pay[pay.accepted_golden].copy(); pg=pg.merge(accounts[['account_id','borrower_id','outstanding_amount','dpd','risk_segment','loan_type','status']],on='account_id',how='left',suffixes=('_payment','_master'))
pg['borrower_match']=pg.borrower_id_payment.eq(pg.borrower_id_master)
pg['month']=month(pg.event_at); save(pg,'golden_payments')
# Contact/engagement events standardized
calls=tables['calls'].copy(); calls['event_at']=pd.to_datetime(calls.event_at,errors='coerce'); calls['month']=month(calls.event_at)
wa=tables['whatsapp_events'].copy(); wa['event_at']=pd.to_datetime(wa.event_at,errors='coerce'); wa['month']=month(wa.event_at)
sms=tables['sms_events'].copy(); sms['event_at']=pd.to_datetime(sms.event_at,errors='coerce'); sms['month']=month(sms.event_at)
vis=tables['field_visits'].copy(); vis['event_at']=pd.to_datetime(vis.event_at,errors='coerce'); vis['month']=month(vis.event_at)
ptp=tables['promises_to_pay'].copy(); ptp['event_at']=pd.to_datetime(ptp.event_at,errors='coerce'); ptp['promised_date']=pd.to_datetime(ptp.promised_date,errors='coerce'); ptp['month']=month(ptp.event_at)
# Monthly KPIs
months=sorted(set(pg.month.dropna()))
monthly=[]
for m in months:
 p=pg[pg.month==m]; c=calls[calls.month==m]; q=ptp[ptp.month==m]; v=vis[vis.month==m]; w=wa[wa.month==m]; s=sms[sms.month==m]
 succ_calls=c[c.call_status.astype(str).str.upper().eq('ANSWERED')]
 monthly.append({'month':m,'successful_recovery_amount':round(p.amount.sum(),2),'successful_payment_count':len(p),'unique_paying_accounts':p.account_id.nunique(),'successful_payments_per_1000_accounts':round(1000*p.account_id.nunique()/accounts.account_id.nunique(),2),'recovery_per_account_rupees':round(p.amount.sum()/accounts.account_id.nunique(),2),'call_attempts':len(c),'answered_calls':len(succ_calls),'call_answer_rate':round(len(succ_calls)/len(c),4) if len(c) else np.nan,'ptp_created':len(q),'ptp_kept':int(q.status.astype(str).str.upper().eq('KEPT').sum()),'ptp_kept_rate_observed':round(q.status.astype(str).str.upper().eq('KEPT').mean(),4) if len(q) else np.nan,'field_visits':len(v),'whatsapp_events':len(w),'sms_events':len(s)})
mon=pd.DataFrame(monthly); mon['mom_recovery_change_pct']=mon.successful_recovery_amount.pct_change()*100; mon['mom_recovery_change_pct']=mon['mom_recovery_change_pct'].replace([np.inf,-np.inf],np.nan); save(mon,'monthly_recovery_kpis')
# Attribution: direct source only for PTP; no payment-level campaign id; report unattributed rather than last touch
ptp['source']=ptp.source.fillna('UNKNOWN'); source_ptp=ptp.groupby('source').agg(ptps=('ptp_id','count'),kept=('status',lambda x:(x.astype(str).str.upper()=='KEPT').sum())).reset_index(); source_ptp['kept_rate']=source_ptp.kept/source_ptp.ptps; save(source_ptp,'ptp_source_performance')
# Channel funnel event outcome definitions (descriptive, not deduplicated borrower-level causal conversion)
channel=[]
for nm,d,event_col,success_values in [('VOICE',calls,'call_status',['ANSWERED']),('WHATSAPP',wa,'event_type',['DELIVERED','READ','CLICKED']),('SMS',sms,'event_type',['DELIVERED','CLICKED']),('FIELD',vis,'outcome',['CONTACTED','PTP','PAID'])]:
 for m,g in d.groupby('month'):
  channel.append({'channel':nm,'month':m,'events':len(g),'positive_events':g[event_col].astype(str).str.upper().isin(success_values).sum(),'positive_event_rate':g[event_col].astype(str).str.upper().isin(success_values).mean(),'unique_accounts':g.account_id.nunique()})
ch=pd.DataFrame(channel); save(ch,'channel_performance')
# Operational performance by vendor, agent, DPD/risk, geo
vendor=calls.merge(tables['vendor_telephony'][['vendor_id','vendor_name','schema_version']],on='vendor_id',how='left')
vend=vendor.groupby(['vendor_id','vendor_name','schema_version']).agg(calls=('call_id','count'),answered=('call_status',lambda x:(x.astype(str).str.upper()=='ANSWERED').sum()),mean_duration=('duration_sec','mean')).reset_index(); vend['answer_rate']=vend.answered/vend.calls; save(vend,'vendor_performance')
agentcalls=calls.merge(agents[['agent_id','employee_code','team','vendor_id','joined_at']],on='agent_id',how='left',suffixes=('','_agent'))
agentperf=agentcalls.groupby(['agent_id','employee_code','team']).agg(calls=('call_id','count'),answered=('call_status',lambda x:(x.astype(str).str.upper()=='ANSWERED').sum()),avg_duration_sec=('duration_sec','mean')).reset_index(); agentperf['answer_rate']=agentperf.answered/agentperf.calls; save(agentperf,'agent_performance')
acct=accounts.merge(borrowers[['borrower_id','city','state']],on='borrower_id',how='left'); save(acct.groupby(['dpd','risk_segment']).agg(accounts=('account_id','nunique'),outstanding=('outstanding_amount','sum')).reset_index(),'portfolio_dpd_risk')
save(acct.groupby(['state','city']).agg(accounts=('account_id','nunique'),outstanding=('outstanding_amount','sum'),avg_dpd=('dpd','mean')).reset_index(),'geography_portfolio')
# Cohort / roll-rate from observed status-history transitions (event-based, no fixed monthly snapshot)
h=tables['account_status_history'].copy(); h['event_at']=pd.to_datetime(h.event_at,errors='coerce'); h=h.sort_values(['account_id','event_at']); h['prior_status']=h.groupby('account_id').status.shift(); h['month']=month(h.event_at)
trans=h[h.prior_status.notna()].groupby(['prior_status','status']).size().reset_index(name='transition_count'); save(trans,'status_transition_matrix')
# targeting/campaign strategy analysis
camp=tables['campaigns'].copy(); tgt=tables['daily_targeting'].merge(camp[['campaign_id','campaign_name','channel','strategy_version']],on='campaign_id',how='left'); tgt['target_date']=pd.to_datetime(tgt.target_date,errors='coerce'); tgt['month']=month(tgt.target_date)
tgtm=tgt.groupby(['month','strategy_version','recommended_channel']).agg(target_records=('target_id','count'),unique_accounts=('account_id','nunique'),contacted=('status',lambda x:(x.astype(str).str.upper()=='CONTACTED').sum())).reset_index(); tgtm['contacted_rate']=tgtm.contacted/tgtm.target_records; save(tgtm,'targeting_strategy_performance')
# Statistical investigation: monthly mix and strategy associations; do not label causal
# Monthly distribution / mix and Simpson-style stratified descriptive rates
mix=acct.groupby(['loan_type','risk_segment']).agg(accounts=('account_id','nunique'),outstanding=('outstanding_amount','sum'),avg_dpd=('dpd','mean')).reset_index(); save(mix,'portfolio_mix')
# payment amounts by risk and loan type
payseg=pg.groupby(['risk_segment','loan_type']).agg(recovered=('amount','sum'),payments=('payment_id','count'),accounts=('account_id','nunique')).reset_index(); save(payseg,'recovery_by_segment')
# timezone / out-of-hours diagnostic: event timestamps are naive local-ish strings with multiple timezone labels; cannot safely UTC convert
calls['local_hour']=calls.event_at.dt.hour; calls['after_hours_flag']=(calls.local_hour<8)|(calls.local_hour>=20)
timezone=calls.groupby('timezone').agg(calls=('call_id','count'),after_hours=('after_hours_flag','sum'),answer_rate=('call_status',lambda x:(x.astype(str).str.upper()=='ANSWERED').mean())).reset_index(); timezone['after_hours_rate']=timezone.after_hours/timezone.calls; save(timezone,'timezone_forensics')
# Forensic issue register
issues=pd.DataFrame([
['Coverage','Payment events span Jan-Aug 2026; calls have a Dec 2025 edge event; this is not a full 12 months','Observed source min/max timestamps by table','High','Do not claim 12-month trend; request missing months'],
['Recovery definition','No supplied prior leadership metric definition or historical denominator','Assignment asks to challenge definitions; payment table has no campaign id','High','Use successful net payments / static accounts as directional proxy only'],
['Payment attribution','Payment records have provider_id but no campaign_id or interaction_id','Schema inspection','High','Do not attribute recovery to latest touch; label unattributed'],
['Payment deduplication','Duplicate payment_reference values checked; only reference-level repeats excluded','payment_reference key profiling','Medium','Keep exceptions; validate against processor ledger'],
['Identity','Event borrower IDs can disagree with account master borrower ID','Cross-table account-borrower join','High','Use account master for account ownership; retain event mismatch exceptions'],
['Timezones','Multiple timezone labels with naive timestamps','calls.timezone and event_at inspection','High','No UTC conversion without source-system semantics'],
['Historical states','Status history is event log; account master is latest snapshot','event_at/recorded_at comparison','Medium','Use event log for transitions, not overwritten master as history'],
['Targeting','Campaign strategy versions and target statuses are descriptive; no random assignment','campaigns + daily_targeting','High','Counterfactual requires controlled holdout or defensible quasi-experiment'],
['Agent identity','Employee code used as deterministic alias; multi-ID conflicts retained','agents.employee_code grouping','Medium','Review collisions before canonical merge'],
['Channel conversion','Events are not a common denominator and event success definitions differ','channel event schemas','High','Do not compare channel event rates as causal ROI']
],columns=['issue','finding','method','severity','treatment_or_next_step']); save(issues,'data_quality_issue_register')
# Quality impact summary
impact=pd.DataFrame([
['Raw payment rows',len(pay)],['Successful positive payment rows',int(pay.is_success.sum())],['Duplicate payment references flagged',int(pay.duplicate_reference.sum())],['Golden accepted payments',int(pay.accepted_golden.sum())],['Non-success/nonpositive payment rows',int((~pay.is_success).sum())],['Account-borrower mismatch pairs',int(rel.mismatch.sum())],['Agent employee-code groups needing review',int((agent_conf.resolution_status=='REVIEW_REQUIRED').sum())]
],columns=['measure','count']); save(impact,'cleaning_impact_summary')
# Campaign attribution limits + counterfactual design
counter=pd.DataFrame([
['Treatment','Accounts first exposed to post-change targeting strategy (define strategy-change date from campaign metadata)'],['Control','Eligible accounts not exposed in same period, matched on pre-period DPD, outstanding, risk, loan type, geography and prior engagement'],['Outcome','Successful net payment amount per eligible account over fixed 30/60-day window'],['Method','Propensity-score weighting or matching + difference-in-differences with account and calendar-time controls'],['Assumptions','Parallel trends, no spillovers, stable eligibility, accurate exposure dates, no unmeasured time-varying confounding'],['Limitations','Current extracts do not provide immutable exposure assignment or a clear single intervention date; results cannot be causal from available data alone'],['Preferred test','Randomized account-level holdout stratified by DPD/risk/client; pre-register primary metric and guardrails']
],columns=['element','design']); save(counter,'counterfactual_design')
# SQL analytical views
sql='''-- Collections analytics: curated analytical views (SQLite)\nDROP VIEW IF EXISTS golden_successful_payments;\nCREATE VIEW golden_successful_payments AS\nSELECT p.* FROM raw_payments p\nWHERE UPPER(COALESCE(p.payment_status,''))='SUCCESS' AND CAST(p.amount AS REAL)>0\nAND p.payment_id IN (SELECT MIN(payment_id) FROM raw_payments GROUP BY payment_reference,account_id,amount,payment_status)
AND p.payment_reference NOT IN (SELECT payment_reference FROM raw_payments GROUP BY payment_reference HAVING COUNT(DISTINCT account_id || '|' || amount || '|' || payment_status)>1);\n\nDROP VIEW IF EXISTS monthly_recovery;\nCREATE VIEW monthly_recovery AS\nSELECT substr(event_at,1,7) AS month, COUNT(*) AS payment_count, COUNT(DISTINCT account_id) AS paying_accounts, SUM(CAST(amount AS REAL)) AS recovered_amount\nFROM golden_successful_payments GROUP BY substr(event_at,1,7);\n\nDROP VIEW IF EXISTS call_monthly;\nCREATE VIEW call_monthly AS\nSELECT substr(event_at,1,7) AS month, COUNT(*) AS calls, SUM(CASE WHEN UPPER(call_status)='ANSWERED' THEN 1 ELSE 0 END) AS answered,\n1.0*SUM(CASE WHEN UPPER(call_status)='ANSWERED' THEN 1 ELSE 0 END)/COUNT(*) AS answer_rate FROM raw_calls GROUP BY substr(event_at,1,7);\n\n-- Identity mismatch exception query\nSELECT DISTINCT c.account_id,c.borrower_id AS event_borrower_id,a.borrower_id AS master_borrower_id\nFROM raw_calls c JOIN raw_accounts a USING(account_id) WHERE c.borrower_id<>a.borrower_id;\n\n-- Duplicate payment references: inspect, do not delete blindly\nSELECT payment_reference,COUNT(*) AS rows,COUNT(DISTINCT account_id) AS accounts,COUNT(DISTINCT amount) AS amounts\nFROM raw_payments GROUP BY payment_reference HAVING COUNT(*)>1;\n\n-- PTP kept rate by declared source\nSELECT source,COUNT(*) AS ptps,SUM(CASE WHEN UPPER(status)='KEPT' THEN 1 ELSE 0 END) AS kept,\n1.0*SUM(CASE WHEN UPPER(status)='KEPT' THEN 1 ELSE 0 END)/COUNT(*) AS kept_rate\nFROM raw_promises_to_pay GROUP BY source;\n'''
(ROOT/'sql'/'collections_analytics.sql').write_text(sql)
# Charts
plt.figure(figsize=(10,4)); plt.bar(mon.month,mon.successful_recovery_amount); plt.xticks(rotation=45); plt.title('Monthly successful payment amount (₹)'); plt.ylabel('₹'); plt.tight_layout(); plt.savefig(VIZ/'monthly_recovery.png',dpi=160); plt.close()
plt.figure(figsize=(10,4)); plt.plot(mon.month,mon.call_answer_rate,marker='o',label='Call answer rate'); plt.plot(mon.month,mon.ptp_kept_rate_observed,marker='o',label='Observed PTP kept rate'); plt.xticks(rotation=45); plt.ylim(0,1); plt.legend(); plt.title('Operational rates (definitions differ)'); plt.tight_layout(); plt.savefig(VIZ/'operational_rates.png',dpi=160); plt.close()
plt.figure(figsize=(9,4)); x=vend.sort_values('answer_rate'); plt.bar(x.vendor_name.fillna(x.vendor_id),x.answer_rate); plt.xticks(rotation=45,ha='right'); plt.title('Telephony vendor call answer rate'); plt.tight_layout(); plt.savefig(VIZ/'vendor_answer_rate.png',dpi=160); plt.close()
plt.figure(figsize=(9,4)); plt.bar(payseg.risk_segment+' / '+payseg.loan_type,payseg.recovered); plt.xticks(rotation=70,ha='right'); plt.title('Recovered amount by risk and loan type'); plt.tight_layout(); plt.savefig(VIZ/'segment_recovery.png',dpi=160); plt.close()
# Architecture diagram as Mermaid source and PNG schematic
(ROOT/'docs'/'architecture.mmd').write_text('''flowchart LR\n A[Source CSVs / APIs] --> B[Raw immutable zone]\n B --> C[Staging: schema + type checks]\n C --> D[Clean: dedupe + identity crosswalks]\n D --> E[Golden: account / borrower / payment facts]\n E --> F[Feature layer: DPD, channel, agent, cohort]\n F --> G[Metric layer: recovery + funnel + cost]\n G --> H[Executive dashboard]\n C --> Q[Data quality exceptions]\n D --> Q\n E --> M[Lineage + audit log]\n F --> N[Anomaly monitoring]\n''')
# Summary metrics and cautious memo
latest=mon.iloc[-1] if len(mon) else None
first=mon.iloc[0] if len(mon) else None
mom_valid=mon.dropna(subset=['mom_recovery_change_pct'])
max_mom=mom_valid.loc[mom_valid.mom_recovery_change_pct.idxmax()] if len(mom_valid) else None
min_mom=mom_valid.loc[mom_valid.mom_recovery_change_pct.idxmin()] if len(mom_valid) else None
summary={'payment_event_months':mon.month.tolist(),'successful_golden_payment_rows':int(len(pg)),'successful_golden_recovery_rupees':round(float(pg.amount.sum()),2),'raw_payment_rows':len(pay),'payment_reference_duplicates':int(pay.duplicate_reference.sum()),'account_borrower_mismatch_pairs':int(rel.mismatch.sum()),'agent_employee_code_review_groups':int((agent_conf.resolution_status=='REVIEW_REQUIRED').sum()),'latest_month':str(latest.month) if latest is not None else None,'latest_month_recovery':float(latest.successful_recovery_amount) if latest is not None else None,'max_mom_month':str(max_mom.month) if max_mom is not None else None,'max_mom_pct':float(max_mom.mom_recovery_change_pct) if max_mom is not None else None,'min_mom_month':str(min_mom.month) if min_mom is not None else None,'min_mom_pct':float(min_mom.mom_recovery_change_pct) if min_mom is not None else None,'claim_verdict':'NOT VERIFIABLE from supplied extracts: payment events cover Jan-Aug 2026 only; no supplied leadership metric definition, monthly eligible balance denominator, cost data, or payment-to-campaign key.'}
(OUT/'executive_metrics.json').write_text(json.dumps(summary,indent=2))
# executive memo
memo=f'''# Executive Memo — Collections Analytics\n\n## Decision in one minute\nThe supplied extract does **not** support a defensible confirmation of “recovery improved by 11% month-on-month.” The observed event coverage is {mon.month.min() if len(mon) else 'N/A'} to {mon.month.max() if len(mon) else 'N/A'} ({len(mon)} observed months), not 12 months. The extracts also lack the historical eligible-balance denominator, a documented legacy KPI definition, cost data and a payment-to-campaign interaction key. The 11% claim is therefore **not verifiable**, rather than proven false.\n\n## What happened\nThe independently curated payment view retains positive SUCCESS payments and excludes repeated payment references conservatively. It contains {len(pg):,} accepted rows totalling ₹{pg.amount.sum():,.0f}. Monthly amounts and operational indicators are in `outputs/monthly_recovery_kpis.csv`. This is gross successful payment amount, not net cash after reversals/settlement or a true recovery rate. The current account master is a static snapshot; it is not a valid monthly denominator.\n\n## Why it happened / confidence\nDescriptive variation exists across channel, vendor, agent, risk and geography cuts. These are **correlations**, not causal effects. Calls, WhatsApp, SMS and field events have different event definitions and cannot be compared as if they share a common conversion denominator. Payment rows have no campaign or interaction id, so last-touch attribution would be fabricated. Multiple timezone labels coexist with naive timestamps; no UTC conversion is defensible without source-system semantics.\n\n## Data quality and cleaning impact\nSee `outputs/cleaning_impact_summary.csv`, `outputs/data_quality_issue_register.csv` and `outputs/payment_exceptions.csv`. Account ownership is taken from `accounts` for account-level joins; mismatching event borrower IDs are preserved as exceptions. Agent aliases are grouped by employee_code, but ambiguous groups are flagged for review.\n\n## ₹10 Cr recommendation\n**Do not commit the full ₹10 Cr to one intervention based on these observational extracts.** The assignment explicitly permits saying evidence is insufficient. Run a 6–8 week randomized holdout before scaling: stratify accounts by DPD, risk, outstanding, geography and loan type; randomize eligible accounts to current strategy versus the proposed investment intervention; measure incremental net successful collections per eligible account, cost per incremental ₹ recovered, complaints and promise-kept rate.\n\nIf leadership requires a near-term direction, prioritize a controlled **borrower-targeting experiment** rather than a broad vendor/agent/AI rollout: it is measurable, reversible and creates the counterfactual needed to estimate incrementality. This is a test recommendation, not a claim that targeting has already caused higher recovery.\n\n## Financial model and break-even\nA credible incremental recovery / ROI / break-even estimate cannot be calculated because unit costs, investment quotes, net-recovery definition, recoverable balance and causal lift are absent. For a ₹10 Cr investment, break-even incremental net recovery is at least ₹10 Cr before operating costs; ROI = (incremental net recovery − ₹10 Cr − incremental operating cost) / (₹10 Cr + incremental operating cost). Populate low/base/high lift from the randomized test before approval.\n\n**Confidence:** High that the 11% claim is not verifiable from this extract; medium on the descriptive cleaned-payment totals; low on channel/vendor/agent causal ranking; no defensible causal estimate for ₹10 Cr yet.\n'''
(REP/'Executive_Memo.md').write_text(memo)
# Data quality report PDF
styles=getSampleStyleSheet(); story=[Paragraph('Collections Analytics — Full Project Report',styles['Title']),Paragraph('Independent reconstruction, data forensics, KPI design, counterfactual and production analytics design',styles['Heading2']),Spacer(1,8)]
story.append(Paragraph('<b>Executive conclusion:</b> The reported 11% month-on-month improvement is not verifiable from the supplied extracts. Observed event coverage is Jan–Aug 2026 only, with no documented historical denominator, legacy KPI formula, cost data or payment-to-campaign key.',styles['BodyText'])); story.append(Spacer(1,8))
story.append(Paragraph('1. Data coverage and curated payment facts',styles['Heading1']))
data=[['Measure','Value'],['Raw payment rows',f'{len(pay):,}'],['Accepted successful payment rows',f'{len(pg):,}'],['Accepted successful payment amount',f'₹{pg.amount.sum():,.0f}'],['Repeated payment references flagged',f'{int(pay.duplicate_reference.sum()):,}'],['Account-borrower mismatch pairs',f'{int(rel.mismatch.sum()):,}'],['Months represented',f'{len(mon)} ({mon.month.min()} to {mon.month.max()})']]
t=Table(data,colWidths=[95*mm,75*mm]); t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#203864')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('GRID',(0,0),(-1,-1),.4,colors.grey),('PADDING',(0,0),(-1,-1),6)])); story.append(t)
story.append(Spacer(1,8)); story.append(Image(str(VIZ/'monthly_recovery.png'),width=170*mm,height=68*mm))
story.append(Paragraph('2. KPI definitions',styles['Heading1']))
for x in ['Recovery amount: sum of positive SUCCESS payment rows after conservative payment_reference deduplication. Excludes pending, failed and reversed events.','Recovery rate (preferred): net successful cash collected in a fixed period / eligible opening outstanding balance for the same frozen account population. The required monthly opening balance snapshot is not supplied.','Contact rate: unique eligible accounts with a verified two-way human contact / unique eligible accounts attempted. Current call ANSWERED is only an answer proxy, not verified RPC.','RPC rate: unique accounts with right-party contact / unique accounts attempted. Requires a validated disposition mapping; current codes differ by version and need governance.','PTP rate: unique accounts with a valid PTP / unique accounts with RPC. PTP kept rate: matured PTPs with matched successful payment by promised date / matured PTPs. Current status field is not independently reconciled to payments.','Recovery per account: net successful recovery / fixed eligible accounts. Recovery per agent-hour: net recovery / logged productive agent hours; sessions are available but overlap and non-voice channels complicate attribution.','Cost per ₹ recovered: fully loaded channel + vendor + agent + field cost / net successful recovery. Cost tables are absent.']:
 story.append(Paragraph('• '+x,styles['BodyText'])); story.append(Spacer(1,4))
story.append(Paragraph('3. Data forensics and golden-layer rules',styles['Heading1']))
for x in ['Raw files are immutable and loaded to SQLite raw_* tables.','Accounts is the account ownership source for borrower_id; event-level disagreements are retained as exception rows, never silently overwritten.','Agent employee_code is used as a deterministic alias key only where unambiguous; collisions are review-required.','Only positive SUCCESS payments enter the golden payment fact. Repeated payment_reference values are excluded conservatively and retained in exceptions for processor-ledger review.','Payment campaign attribution is not available; no last-touch attribution is applied.','Naive timestamps with timezone labels are not shifted to UTC without documented source semantics.','Account status history is treated as an event log; the accounts table is a current snapshot, not historical monthly status.']:
 story.append(Paragraph('• '+x,styles['BodyText'])); story.append(Spacer(1,4))
story.append(Paragraph('4. Statistical investigation and counterfactual',styles['Heading1']))
story.append(Paragraph('The analysis provides descriptive stratification by risk, DPD, loan type, geography, channel, vendor and agent. These are facts about observed associations, not causal drivers. Strategy-version comparisons are vulnerable to selection bias and time effects. A defensible design is a stratified randomized holdout; a matched DiD can be a secondary design only if pre-trends and treatment timing are supportable.',styles['BodyText']))
story.append(Paragraph('5. ₹10 Cr decision',styles['Heading1']))
story.append(Paragraph('Do not deploy the full amount on the current evidence. Run a 6–8 week randomized targeting pilot, then estimate incremental net recovery and cost. Break-even requires incremental net recovery ≥ ₹10 Cr plus incremental operating costs. A numerical ROI forecast would be invented because costs and causal lift are not present.',styles['BodyText']))
story.append(Paragraph('6. Production design',styles['Heading1']))
story.append(Paragraph('Raw immutable ingestion → staging schema/type validation → clean identity and deduplication rules → golden account/payment/event facts → feature layer (DPD, risk, cohort, channel, agent) → governed metric layer → one-screen dashboard. Add data contracts, primary-key checks, freshness monitoring, late-arriving event watermarks, idempotent backfills, lineage and anomaly alerts. See docs/architecture.mmd.',styles['BodyText']))
story.append(Paragraph('7. Deliverable index',styles['Heading1']))
story.append(Paragraph('Python: src/run_full_project.py. SQL: sql/collections_analytics.sql. Dashboard: dashboard/app.py. Notebook: notebooks/02_full_analysis.ipynb. Golden outputs and exceptions: outputs/. Executive memo: reports/Executive_Memo.md. Architecture: docs/architecture.mmd.',styles['BodyText']))
SimpleDocTemplate(str(REP/'Full_Collections_Analytics_Report.pdf'),pagesize=A4,rightMargin=16*mm,leftMargin=16*mm,topMargin=15*mm,bottomMargin=15*mm).build(story)
print(json.dumps(summary,indent=2))

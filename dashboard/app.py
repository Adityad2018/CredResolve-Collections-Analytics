from pathlib import Path
import json
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"

st.set_page_config(
    page_title="CredResolve | Collections Intelligence",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CredResolve management visual system
NAVY, INK, MUTED = "#101B2D", "#17243A", "#68788D"
TEAL, BLUE, AMBER, RED = "#0D9488", "#4776E6", "#D97706", "#C2414B"
PALE = "#F4F7FB"

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@500;600;700;800&display=swap');
html, body, [class*="css"] {font-family:'DM Sans',sans-serif;}
.stApp {background:#F7F8F6;color:#17243A;}
.stApp {background:#F4F7FB;color:#17243A;}
.block-container {padding-top:1.2rem;padding-bottom:2.2rem;max-width:1580px;}
[data-testid="stSidebar"] {background:#101B2D;}
[data-testid="stSidebar"] * {color:#E7EEF8 !important;}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p {color:#AFC0D5 !important;}
.hero {background:linear-gradient(115deg,#102A43 0%,#173F5F 68%,#176B67 100%);padding:1.65rem 1.9rem;border-radius:5px;color:white;margin-bottom:1.15rem;box-shadow:0 5px 18px rgba(16,27,45,.09);}
.hero-kicker {color:#80D8D0;text-transform:uppercase;letter-spacing:.14em;font-size:.7rem;font-weight:800;}
.hero h1 {color:white;font-family:Manrope,sans-serif;font-size:1.8rem;font-weight:800;margin:.35rem 0 .25rem;}
.hero p {color:#C7D5E6;margin:0;font-size:.92rem;}
.kicker {color:#0D9488;font-size:.7rem;text-transform:uppercase;letter-spacing:.13em;font-weight:800;margin:0 0 .2rem;}
.section-title {color:#17243A;font-family:Manrope,sans-serif;font-size:1.2rem;font-weight:800;margin:.05rem 0 .7rem;}
.metric-card {background:white;border:1px solid #E1E6E9;border-radius:4px;padding:1rem 1.1rem;min-height:112px;box-shadow:0 1px 3px rgba(20,38,62,.025);}
.metric-label {color:#68788D;font-size:.72rem;font-weight:700;letter-spacing:.04em;margin-bottom:.45rem;}
.metric-value {color:#17243A;font-family:Manrope,sans-serif;font-size:1.62rem;line-height:1.15;font-weight:800;}
.metric-note {color:#7A899B;font-size:.69rem;margin-top:.42rem;}
.panel {background:white;border:1px solid #E1E6E9;border-radius:4px;padding:1rem 1.1rem;}
.callout {padding:.85rem 1rem;border-radius:11px;border-left:4px solid #D97706;background:#FFF8EB;color:#6D4A12;font-size:.86rem;}
.callout.bad {border-left-color:#C2414B;background:#FFF0F0;color:#7F252D;}
.callout.good {border-left-color:#0D9488;background:#EAF8F6;color:#145B55;}
.small {color:#718096;font-size:.76rem;}
div[data-testid="stMetric"] {background:white;border:1px solid #E4EAF1;padding:12px 15px;border-radius:13px;}
hr {border-color:#E5EAF1;}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_csv(name):
    p = OUT / name
    if not p.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(p)
    except Exception as exc:
        st.warning(f"Could not read {name}: {exc}")
        return pd.DataFrame()

@st.cache_data(show_spinner=False)
def read_json(name):
    p = OUT / name
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}

def section(kicker, title):
    st.markdown(f"<div class='kicker'>{kicker}</div><div class='section-title'>{title}</div>", unsafe_allow_html=True)

def card(label, value, note=""):
    st.markdown(
        f"<div class='metric-card'><div class='metric-label'>{label}</div>"
        f"<div class='metric-value'>{value}</div><div class='metric-note'>{note}</div></div>",
        unsafe_allow_html=True,
    )

def cr(v):
    return f"₹{float(v)/1e7:,.2f} Cr"

def add_12_month_frame(df, start="2026-01"):
    """Build a display frame; absent months remain null, never zero-filled."""
    if df.empty or "month" not in df.columns:
        return pd.DataFrame()
    x = df.copy()
    x["month"] = x["month"].astype(str).str[:7]
    months = pd.date_range(f"{start}-01", periods=12, freq="MS").strftime("%Y-%m")
    frame = pd.DataFrame({"month": months}).merge(x, on="month", how="left")
    observed = set(x["month"].dropna())
    frame["coverage"] = frame["month"].map(
        lambda m: "Observed · partial" if m == "2026-08" and m in observed
        else ("Observed" if m in observed else "Not supplied")
    )
    return frame

# Load only curated outputs. Do not use old channel_performance positive-event rates.
metrics = read_json("executive_metrics.json")
golden = read_csv("golden_payments.csv")
monthly = read_csv("monthly_recovery_kpis.csv")
gru_monthly_forecast = read_csv("six_month_model_monthly_forecasts.csv")
segments = read_csv("recovery_by_segment.csv")
campaign = read_csv("campaign_date_reliability.csv")
channel_assoc = read_csv("channel_payment_association_maturity_adjusted.csv")
cleaning = read_csv("cleaning_impact_summary.csv")
ptp = read_csv("ptp_source_performance.csv")
portfolio = read_csv("portfolio_mix.csv")
dpd = read_csv("portfolio_dpd_risk.csv")

# Prefer the revised Golden Dataset over stale summary JSON values.
if not golden.empty:
    golden_rows = len(golden)
    amount_col = "amount" if "amount" in golden.columns else None
    recovery = float(pd.to_numeric(golden[amount_col], errors="coerce").fillna(0).sum()) if amount_col else float(metrics.get("successful_golden_recovery_rupees", 0) or 0)
    payers = int(golden["account_id"].nunique()) if "account_id" in golden.columns else None
    payment_ids = int(golden["payment_id"].nunique()) if "payment_id" in golden.columns else golden_rows
else:
    golden_rows = int(metrics.get("successful_golden_payment_rows", 0) or 0)
    recovery = float(metrics.get("successful_golden_recovery_rupees", 0) or 0)
    payers = None
    payment_ids = golden_rows

months_observed = len(monthly) if not monthly.empty else len(metrics.get("payment_event_months", []))
within_pct = None
if not campaign.empty and {"targeting_rows", "valid_rows"}.issubset(campaign.columns):
    denom = pd.to_numeric(campaign.targeting_rows, errors="coerce").fillna(0).sum()
    numer = pd.to_numeric(campaign.valid_rows, errors="coerce").fillna(0).sum()
    within_pct = (numer / denom * 100) if denom else None

with st.sidebar:
    st.markdown("<div style='font-family:Manrope;font-size:1.25rem;font-weight:800;color:white'>◈ CREDRESOLVE</div><div style='font-size:.68rem;letter-spacing:.14em;color:#80D8D0;margin-top:3px'>COLLECTIONS INTELLIGENCE</div>", unsafe_allow_html=True)
    st.markdown("---")
    page = st.radio("MANAGEMENT WORKSPACE", [
        "Executive command centre", "12-month performance", "Portfolio intelligence",
        "Channel & campaign", "6-month forecast (AdamW)", "Model comparison (Adam / GRU / LSTM)", "Data trust centre", "Strategic SWOT", "₹10 Cr investment decision"
    ], label_visibility="visible")
    st.markdown("---")
    st.caption("Assignment horizon: approximately 12 months")
    st.caption("Payment coverage in supplied extract: Jan–Aug 2026")
    st.caption("August is partial; Sep–Dec are unavailable in this extract.")
    st.markdown("---")
    st.caption("Prepared for CredResolve · Analytical reconstruction · INR")

st.markdown("<div class='hero'><div class='hero-kicker'>Management decision platform · Collections strategy</div><h1>Collections performance. Evidence. Capital allocation.</h1><p>Is the reported 11% improvement genuine — and where should CredResolve deploy its next ₹10 crore?</p></div>", unsafe_allow_html=True)

if page == "Executive command centre":
    section("01 / EXECUTIVE READOUT", "The management decision in one view")
    cols = st.columns(4)
    values = [
        ("GROSS SUCCESSFUL RECOVERY", cr(recovery), "Golden payments · not incremental lift"),
        ("GOLDEN PAYMENT RECORDS", f"{golden_rows:,}", "Unique payment IDs after reconciliation"),
        ("PAYMENT COVERAGE", f"{months_observed} / 12 months", "Eight observed months; August partial"),
        ("11% PERFORMANCE CLAIM", "NOT VERIFIABLE", "No governed denominator or KPI definition"),
    ]
    for c, (label, value, note) in zip(cols, values):
        with c: card(label, value, note)
    st.markdown("<div style='height:10px'></div><div class='callout bad'><b>11% recovery claim:</b> March 2026 gross recovery rose 11.03% month-on-month, but this is one monthly movement—not evidence of a sustained 11% recovery-rate improvement. The headline claim is NOT VERIFIABLE without the official KPI definition and historical eligible-balance denominator. <b>₹10 Cr investment decision:</b> do not deploy the full amount yet; authorize a controlled 6–8 week borrower-targeting pilot, then stage-gate further capital on measured incremental net recovery and cost.</div>", unsafe_allow_html=True)

    left, right = st.columns([1.55, 1])
    with left:
        section("RECOVERY TRAJECTORY", "Monthly gross successful payments")
        if not monthly.empty and "successful_recovery_amount" in monthly.columns:
            x = monthly.copy()
            x["recovery_cr"] = pd.to_numeric(x.successful_recovery_amount, errors="coerce") / 1e7
            fig = px.bar(x, x="month", y="recovery_cr", text=x.recovery_cr.map(lambda z: f"{z:.1f}" if pd.notna(z) else ""), labels={"month":"Payment month", "recovery_cr":"Gross recovery (₹ Cr)"})
            fig.update_traces(marker_color=TEAL, textposition="outside", cliponaxis=False)
            fig.update_layout(height=330, margin=dict(l=5,r=5,t=20,b=5), plot_bgcolor="white", paper_bgcolor="white", font_color=INK, yaxis_gridcolor="#E9EEF4", xaxis_title=None, yaxis_title="₹ crore")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Monthly recovery output is not present in this project copy.")
    with right:
        section("MANAGEMENT SIGNALS", "Evidence status")
        st.markdown("<div class='panel'>", unsafe_allow_html=True)
        st.markdown("**11% improvement claim**")
        st.markdown(f"<span style='color:{AMBER};font-weight:800'>NOT VERIFIABLE</span>", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Campaign timing integrity**")
        st.markdown(f"<div style='font-size:1.5rem;font-weight:800;color:{RED}'>{within_pct:.2f}%</div><span class='small'>targeting rows within campaign dates</span>" if within_pct is not None else "Not available", unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("**Investment posture**")
        st.markdown(f"<span style='color:{TEAL};font-weight:800'>Controlled pilot before scale</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    section("MANAGEMENT ACTION", "Three gates before capital release")
    a,b,c = st.columns(3)
    with a: card("GATE 01 · DATA", "Reconcile", "Payment, borrower, agent and event identities")
    with b: card("GATE 02 · EVIDENCE", "Randomize", "6–8 week treatment vs holdout pilot")
    with c: card("GATE 03 · CAPITAL", "Stage-gate", "Scale only after net lift and cost are proven")

elif page == "12-month performance":
    section("02 / PERFORMANCE HISTORY", "12-month view — actuals and provisional GRU outlook")
    st.markdown("<div class='callout'><b>Coverage and forecast distinction:</b> January–August 2026 is the observed payment period; August is partial through 8 August. September–December 2026 are shown as GRU forecast values, not actual collections. The assignment's full 12-month historical requirement remains unmet until the missing source months are supplied.</div>", unsafe_allow_html=True)
    if not monthly.empty:
        frame = add_12_month_frame(monthly, "2026-01")
        if not frame.empty and "successful_recovery_amount" in frame:
            frame["recovery_cr"] = pd.to_numeric(frame.successful_recovery_amount, errors="coerce") / 1e7
            frame["display_cr"] = frame["recovery_cr"]
            frame["display_status"] = frame["coverage"]
            if not gru_monthly_forecast.empty:
                gf = gru_monthly_forecast[gru_monthly_forecast.model.astype(str).str.upper().eq("GRU")].copy()
                gf["month"] = gf["month"].astype(str).str[:7]
                gf["forecast_cr"] = pd.to_numeric(gf["forecast_recovery_rupees"], errors="coerce") / 1e7
                gf = gf[gf["month"].between("2026-09", "2026-12")]
                for _, row in gf.iterrows():
                    mask = frame["month"].eq(row["month"])
                    frame.loc[mask, "display_cr"] = row["forecast_cr"]
                    frame.loc[mask, "display_status"] = "GRU forecast · provisional"
            fig = px.bar(frame, x="month", y="display_cr", color="display_status",
                         color_discrete_map={"Observed":TEAL,"Observed · partial":AMBER,
                         "Not supplied":"#DCE3EC","GRU forecast · provisional":BLUE},
                         category_orders={"display_status":["Observed","Observed · partial","GRU forecast · provisional","Not supplied"]},
                         labels={"month":"Month","display_cr":"Gross recovery (₹ Cr)","display_status":"Data status"},
                         hover_data={"display_status":True,"display_cr":":.2f"})
            fig.update_layout(height=390,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=20,b=5),yaxis_gridcolor="#E9EEF4",font_color=INK,xaxis_title=None)
            st.plotly_chart(fig,use_container_width=True)
            show=frame[["month","coverage","display_status"]].copy()
            show["gross_recovery_or_forecast_cr"]=frame.display_cr.round(2)
            for source,target in [("successful_payment_count","successful_payments"),("unique_paying_accounts","paying_accounts")]:
                show[target]=frame[source] if source in frame.columns else pd.NA
            st.dataframe(show,use_container_width=True,hide_index=True)
            st.caption("August is an actual partial-month value. September–December are provisional GRU projections. Unavailable historical actuals remain explicitly identified.")
    else:
        st.warning("Monthly KPI file is missing. The 12-month chart cannot be reconstructed from executive summary metadata alone.")
    if not monthly.empty and "mom_recovery_change_pct" in monthly.columns:
        march=monthly[monthly.month.astype(str).str.endswith("-03")]
        if not march.empty:
            st.info(f"March gross recovery moved {float(march.iloc[0].mom_recovery_change_pct):+.2f}% month-on-month. This is one monthly movement, not evidence of a sustained 11% recovery-rate improvement.")
    st.caption("The supplied history still does not provide 12 complete historical months. Forecasts must not be presented as observed results; obtain the missing source months before claiming a 12-month historical analysis.")

elif page == "6-month forecast (AdamW)":
    section("03 / FORWARD VIEW", "Six-month gross recovery forecast — AdamW neural network")
    forecast = read_csv("adamw_six_month_forecast.csv")
    meta = read_json("adamw_forecast_metadata.json")
    st.markdown("<div class='callout'><b>Forecast status:</b> Experimental model output, not a budget commitment, incremental recovery estimate, or ROI forecast. Training data ends on 8 August 2026; forecast months are September 2026–February 2027.</div>", unsafe_allow_html=True)
    if not forecast.empty:
        forecast["forecast_cr"] = pd.to_numeric(forecast.forecast_recovery_rupees, errors="coerce") / 1e7
        forecast["low_cr"] = pd.to_numeric(forecast.lower_scenario_rupees, errors="coerce") / 1e7
        forecast["high_cr"] = pd.to_numeric(forecast.upper_scenario_rupees, errors="coerce") / 1e7
        total = forecast.forecast_recovery_rupees.sum()
        a,b,c,d = st.columns(4)
        with a: card("6-MONTH FORECAST", cr(total), "Sep 2026–Feb 2027 · gross recovery")
        with b: card("MODEL", "AdamW MLP", "PyTorch · 28-day lookback")
        with c: card("HOLDOUT WMAPE", f"{float(meta.get('holdout_wmape_pct', float('nan'))):.1f}%", "Last 28 observed days")
        with d: card("NAIVE BASELINE", "Better" if not meta.get("beats_naive_baseline_on_holdout_mae", False) else "AdamW better", "7-day mean benchmark on holdout")
        fig = go.Figure()
        if not monthly.empty:
            hist = monthly.copy()
            hist["recovery_cr"] = pd.to_numeric(hist.successful_recovery_amount, errors="coerce") / 1e7
            fig.add_trace(go.Scatter(x=hist.month, y=hist.recovery_cr, mode="lines+markers", name="Observed gross recovery", line=dict(color=TEAL,width=3)))
        fig.add_trace(go.Scatter(x=forecast.month, y=forecast.high_cr, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
        fig.add_trace(go.Scatter(x=forecast.month, y=forecast.low_cr, mode="lines", line=dict(width=0), fill="tonexty", fillcolor="rgba(71,118,230,0.16)", name="Indicative error band"))
        fig.add_trace(go.Scatter(x=forecast.month, y=forecast.forecast_cr, mode="lines+markers", name="AdamW forecast", line=dict(color=BLUE,width=3,dash="dash")))
        fig.update_layout(height=420, plot_bgcolor="white", paper_bgcolor="white", font_color=INK, yaxis_gridcolor="#E9EEF4", xaxis_title=None, yaxis_title="Gross recovery (₹ Cr)", margin=dict(l=5,r=5,t=25,b=5), legend=dict(orientation="h",y=1.12))
        st.plotly_chart(fig, use_container_width=True)
        show=forecast[["month","forecast_cr","low_cr","high_cr","forecast_days"]].copy()
        show.columns=["Month","Forecast ₹ Cr","Lower scenario ₹ Cr","Upper scenario ₹ Cr","Days"]
        for col in show.columns[1:4]: show[col]=show[col].round(2)
        st.dataframe(show,use_container_width=True,hide_index=True)
        st.markdown("**Out-of-sample validation**")
        v1,v2,v3=st.columns(3)
        with v1: st.metric("AdamW holdout MAE", cr(meta.get("holdout_mae_rupees_per_day",0)), "Per day")
        with v2: st.metric("7-day naive MAE", cr(meta.get("naive_7day_mean_holdout_mae_rupees_per_day",0)), "Per day")
        with v3: st.metric("Holdout RMSE", cr(meta.get("holdout_rmse_rupees_per_day",0)), "Per day")
        if not meta.get("beats_naive_baseline_on_holdout_mae", False):
            st.warning("AdamW did not beat the simple 7-day-mean baseline on the 28-day holdout. Keep the forecast as an experimental benchmark; do not use it alone for financial planning.")
        with st.expander("Model setup and limitations"):
            st.write(f"Optimizer: AdamW · learning rate {meta.get('learning_rate')} · weight decay {meta.get('weight_decay')} · lookback {meta.get('lookback_days')} days.")
            st.write("The model learns from 220 daily observations of accepted successful Golden Payments. Calendar features include day-of-week and annual Fourier terms. The final six months are recursive forecasts.")
            for item in meta.get("limitations",[]): st.markdown(f"- {item}")
    else:
        st.warning("Forecast outputs are missing. Run `python src/forecast_adamw.py` from the project root after installing requirements.")

elif page == "Model comparison (Adam / GRU / LSTM)":
    section("04 / MODEL SELECTION", "Preferred forecasting approach: GRU with Adam")
    comparison = read_csv("forecast_model_comparison_metrics.csv")
    monthly_models = read_csv("six_month_model_monthly_forecasts.csv")
    meta_cmp = read_json("forecast_model_comparison_metadata.json")
    st.markdown("<div class='callout'><b>Interpretation:</b> MLP-Adam is a feed-forward neural network trained with Adam. GRU and LSTM are recurrent architectures, also trained with Adam. All use the same 28-day lookback and chronological holdout. This is an experimental comparison, not a validated financial forecast.</div>", unsafe_allow_html=True)
    if not comparison.empty:
        display = comparison.copy()
        display["MAE ₹ lakh/day"] = display["MAE_rupees_per_day"] / 1e5
        display["RMSE ₹ lakh/day"] = display["RMSE_rupees_per_day"] / 1e5
        display = display[["model","optimizer","MAE ₹ lakh/day","RMSE ₹ lakh/day","WMAPE_pct"]]
        display.columns = ["Model","Optimizer","MAE ₹ lakh/day","RMSE ₹ lakh/day","WMAPE %"]
        st.dataframe(display.round(2), use_container_width=True, hide_index=True)
        gru_row = comparison[comparison.model.astype(str).str.upper().eq("GRU")]
        baseline_row = comparison[comparison.model.astype(str).str.lower().str.contains("naive")]
        if not gru_row.empty:
            g = gru_row.iloc[0]
            st.markdown("<div class='callout good'><b>Preferred model — GRU + Adam (provisional).</b> GRU has the lowest holdout MAE, RMSE and WMAPE in this comparison. Its WMAPE is 7.01% versus 10.13% for the 7-day moving-average baseline. We prefer it on observed predictive error, not because it generates the largest forecast total.</div>", unsafe_allow_html=True)
        st.markdown("**Decision rationale**")
        r1, r2, r3 = st.columns(3)
        with r1: card("ACCURACY", "Lowest error", "Best MAE, RMSE and WMAPE on this holdout")
        with r2: card("BENCHMARK", "Beats baseline", "Lower WMAPE than the 7-day mean")
        with r3: card("MODEL PARSIMONY", "GRU over LSTM", "Fewer recurrent components; LSTM did not improve this test")
        st.markdown("<div class='callout'><b>Qualification:</b> One 28-day holdout from 220 daily observations is not enough for production approval. Complete rolling-origin backtests, seed stability, segment-level error analysis and seasonal-naive/ETS comparisons before operational use.</div>", unsafe_allow_html=True)
        fig = px.bar(display, x="Model", y="MAE ₹ lakh/day", color="Model", title="Lower MAE is better — 28-day chronological holdout")
        fig.update_layout(showlegend=False, plot_bgcolor="white", paper_bgcolor="white", font_color=INK, yaxis_gridcolor="#E9EEF4")
        st.plotly_chart(fig, use_container_width=True)
        if not monthly_models.empty:
            monthly_models["forecast_cr"] = pd.to_numeric(monthly_models.forecast_recovery_rupees, errors="coerce") / 1e7
            fig2 = px.line(monthly_models, x="month", y="forecast_cr", color="model", markers=True,
                           labels={"month":"Forecast month","forecast_cr":"Gross recovery (₹ Cr)","model":"Model"},
                           title="Six-month forecast comparison")
            fig2.update_layout(plot_bgcolor="white", paper_bgcolor="white", font_color=INK, yaxis_gridcolor="#E9EEF4")
            st.plotly_chart(fig2, use_container_width=True)
            totals = monthly_models.groupby("model",as_index=False).forecast_recovery_rupees.sum()
            totals["Six-month total ₹ Cr"] = totals.forecast_recovery_rupees / 1e7
            st.dataframe(totals[["model","Six-month total ₹ Cr"]].round(2),use_container_width=True,hide_index=True)
        st.caption(f"Observed window: {meta_cmp.get('observed_start')} to {meta_cmp.get('observed_end')} ({meta_cmp.get('daily_observations')} daily observations). Forecast: Sep 2026–Feb 2027.")
        with st.expander("Methodology and limitations"):
            st.write("The last 28 observed days form a chronological holdout. Models are trained only on earlier observations and recursively predict the holdout. Inputs are the prior 28 daily Golden Payment totals plus calendar features. Adam optimizer and Huber loss are used for MLP, GRU and LSTM. Naive 7-day mean is included as a baseline.")
            for item in meta_cmp.get("limitations",[]): st.markdown(f"- {item}")
    else:
        st.warning("Comparison files are missing. Run `python src/forecast_model_comparison.py` from the project root.")

elif page == "Portfolio intelligence":
    section("03 / PORTFOLIO INTELLIGENCE", "Where recorded recovery is concentrated")
    if not segments.empty and {"risk_segment","loan_type","recovered"}.issubset(segments.columns):
        seg = segments.copy()
        seg["recovery_cr"] = pd.to_numeric(seg.recovered, errors="coerce") / 1e7
        p1,p2 = st.columns(2)
        with p1:
            st.markdown("**Gross recovery by risk segment**")
            risk = seg.groupby("risk_segment", as_index=False).recovery_cr.sum().sort_values("recovery_cr", ascending=False)
            fig = px.bar(risk, x="risk_segment", y="recovery_cr", color="risk_segment", color_discrete_sequence=[BLUE,TEAL,AMBER,RED], labels={"risk_segment":"Risk segment","recovery_cr":"₹ crore"})
            fig.update_layout(showlegend=False,height=330,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=12,b=5),yaxis_gridcolor="#E9EEF4")
            st.plotly_chart(fig,use_container_width=True)
        with p2:
            st.markdown("**Gross recovery by loan type**")
            loan = seg.groupby("loan_type",as_index=False).recovery_cr.sum().sort_values("recovery_cr",ascending=False)
            fig = px.bar(loan,x="loan_type",y="recovery_cr",color="recovery_cr",color_continuous_scale=["#B9D8D4",TEAL],labels={"loan_type":"Loan type","recovery_cr":"₹ crore"})
            fig.update_layout(showlegend=False,height=330,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=12,b=5),yaxis_gridcolor="#E9EEF4",coloraxis_showscale=False)
            st.plotly_chart(fig,use_container_width=True)
        st.markdown("**Risk × loan type detail**")
        st.dataframe(seg, use_container_width=True, hide_index=True)
    else:
        st.info("The recovery-by-segment output is missing or does not have the expected columns.")
    st.markdown("<div class='callout'><b>Interpretation:</b> Segment totals show where successful payments were recorded. They are not segment recovery rates or investment returns: historical eligible balances, exposure denominators and segment-level costs are not supplied.</div>",unsafe_allow_html=True)

elif page == "Channel & campaign":
    section("04 / OPERATING MODEL", "Channel associations and campaign integrity")
    if not channel_assoc.empty:
        st.markdown("**Subsequent-payment association — observational**")
        st.caption("Account-level temporal association after a channel event. Populations differ and accounts may receive several channels; do not interpret as channel conversion or causal lift.")
        st.dataframe(channel_assoc, use_container_width=True, hide_index=True)
    else:
        st.warning("The maturity-adjusted channel association file is missing. The legacy channel_performance file is intentionally not substituted because its positive-event rates are not comparable across channels.")
    st.markdown("---")
    if not campaign.empty and {"campaign_id","targeting_rows","valid_rows","valid_pct"}.issubset(campaign.columns):
        st.markdown("**Campaign date reliability by campaign**")
        cp = campaign.copy()
        cp["valid_pct"] = pd.to_numeric(cp.valid_pct, errors="coerce")
        cp = cp.sort_values("valid_pct", ascending=True)
        fig = px.bar(cp, x="campaign_id", y="valid_pct", color="valid_pct", color_continuous_scale=[RED,AMBER,TEAL], labels={"campaign_id":"Campaign","valid_pct":"Targeting rows within campaign dates (%)"})
        fig.add_hline(y=50,line_dash="dash",line_color="#66758A",annotation_text="50% reference")
        fig.update_layout(height=370,plot_bgcolor="white",paper_bgcolor="white",margin=dict(l=5,r=5,t=20,b=5),yaxis_gridcolor="#E9EEF4",coloraxis_showscale=False,xaxis_title=None)
        st.plotly_chart(fig,use_container_width=True)
        x,y = st.columns(2)
        with x: st.metric("Weighted targeting rows within dates",f"{within_pct:.2f}%" if within_pct is not None else "—")
        with y: st.metric("Campaigns with ≥50% validity",f"{int((cp.valid_pct >= 50).sum())} / {len(cp)}")
        st.dataframe(cp.head(15),use_container_width=True,hide_index=True)
    else:
        st.warning("Campaign reliability output is missing or has an unexpected schema.")
    st.markdown("<div class='callout bad'><b>Do not rank campaigns or strategies.</b> Only 19.69% of targeting rows fall within campaign dates in the validated audit. Reliable exposure assignment and payment-to-campaign linkage are prerequisites for campaign attribution.</div>",unsafe_allow_html=True)

elif page == "Data trust centre":
    section("05 / DATA GOVERNANCE", "What can management safely trust?")
    left,right = st.columns(2)
    with left:
        card("BORROWER–ACCOUNT MISMATCH PAIRS", f"{int(metrics.get('account_borrower_mismatch_pairs',478379)):,}", "Cross-source exception pairs; do not force-match")
        card("AGENT IDENTITY REVIEW GROUPS", f"{int(metrics.get('agent_employee_code_review_groups',1099)):,}", "Ambiguous identity groups require source-owner review")
    with right:
        card("PAYMENT REFERENCES FLAGGED", f"{int(metrics.get('payment_reference_duplicates',7218)):,}", "Reused references are flags, not automatic exclusions")
        card("CAMPAIGN TARGETS WITHIN DATES", f"{within_pct:.2f}%" if within_pct is not None else "Not available", "Campaign exposure timing is unreliable")
    st.markdown("---")
    st.markdown("**Reconciliation and interpretation controls**")
    controls = [
        ("Payment transaction identity", "Use payment_id as the transaction key, subject to source-system confirmation. Consolidate repeated IDs only where non-null source attributes agree. Preserve missing/reused payment_reference values as flags; exclude true payment_id conflicts only."),
        ("Account and borrower identity", "Use account_id for account-level payment analysis. Preserve event borrower_id and account-master borrower_id separately. Do not borrower-aggregate until the cross-source ownership conflicts are reconciled."),
        ("Agent identity", "Do not join the full agent master on agent_id or employee_code where mappings are ambiguous. Agent-level productivity and recovery rankings are not reliable."),
        ("Calls and dispositions", "Keep attempts, calls and dispositions independent. Their call_id links are not account-consistent; do not join them into a fabricated call funnel."),
        ("Digital and field events", "SMS/WhatsApp event sequences and account mappings are inconsistent. Field visit outcomes are not verified settled payments."),
        ("Campaign exposure", "Target dates frequently fall outside campaign start/end dates. Do not use strategy versions for uplift or difference-in-differences ranking."),
        ("Metric governance", "Publish versioned definitions and retain eligible balance, net settled payments, operating costs, actual exposure IDs and event timestamps.")
    ]
    for title, detail in controls:
        with st.expander(title): st.write(detail)
    st.caption("The source issue-register file may contain earlier payment-reference and agent-resolution descriptions. The controls above reflect the revised payment_id-based reconciliation and the later identity audits.")

elif page == "Strategic SWOT":
    section("06 / STRATEGIC POSITION", "SWOT | What the evidence means for CredResolve")
    st.caption("Evidence-led SWOT. Strengths describe what the supplied extracts support; limitations are not reframed as proven operational failures.")
    swot = [
        ("STRENGTHS", TEAL, [
            "A reconciled Golden Payments layer is available for account-level descriptive analysis.",
            "Monthly recovery, paying-account and transaction views can be reconstructed for the observed period.",
            "Portfolio cuts by DPD, risk segment and loan type provide a starting point for management segmentation."
        ]),
        ("WEAKNESSES", RED, [
            "Payment history covers only January–August 2026; August is partial, so the requested 12-month trend is incomplete.",
            "Borrower and agent identity conflicts constrain reliable borrower- and agent-level attribution.",
            "Campaign timing is unreliable; cost, historical eligible-balance and interaction-to-payment linkage are absent."
        ]),
        ("OPPORTUNITIES", BLUE, [
            "Run a stratified randomized holdout to measure incremental recovery from better borrower targeting.",
            "Create governed identity crosswalks and event-level interaction IDs across channels.",
            "Introduce versioned recovery definitions, eligible-balance denominators, net settlement and unit-cost tracking."
        ]),
        ("THREATS", AMBER, [
            "A misleading 11% claim could drive capital allocation before performance is independently verified.",
            "Unreliable campaign and event joins can produce false channel, agent or strategy rankings.",
            "Scaling an intervention without incremental net-recovery and customer-outcome safeguards risks poor returns."
        ])
    ]
    st.markdown("<div class='callout'><b>Executive read-through:</b> the strongest asset is a reconstructed payment fact base; the binding constraint is measurement integrity. The near-term opportunity is a controlled targeting test, while the principal threat is allocating capital on non-causal or incomplete metrics.</div>", unsafe_allow_html=True)
    cols = st.columns(2)
    for idx, (heading, color, bullets) in enumerate(swot):
        with cols[idx % 2]:
            st.markdown(f"<div class='panel' style='border-top:4px solid {color};min-height:230px;margin-bottom:12px'><div style='font-weight:800;letter-spacing:.1em;color:{color};font-size:.78rem'>{heading}</div>", unsafe_allow_html=True)
            for bullet in bullets:
                st.markdown(f"- {bullet}")
            st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("<div class='callout bad'><b>Strategic implication:</b> CredResolve has enough evidence to define a controlled targeting experiment, but not enough to select a winning channel or commit the ₹10 Cr. First repair measurement; then test; then scale.</div>", unsafe_allow_html=True)

elif page == "₹10 Cr investment decision":
    section("07 / CAPITAL ALLOCATION", "Do not scale what has not been measured")
    i1, i2, i3 = st.columns(3)
    with i1: card("CAPITAL UNDER REVIEW", "₹10.00 Cr", "Assignment investment decision")
    with i2: card("CLAIM TO TEST", "11% MoM", "March actual +11.03%; not sustained proof")
    with i3: card("RECOMMENDED ACTION", "Pilot first", "6–8 week randomized targeting test")
    st.markdown("<div class='callout bad'><b>Recommendation:</b> Do not release the full ₹10 Cr to one intervention on the current evidence. The reported 11% recovery improvement is not verifiable as a sustained recovery-rate claim. Run a controlled targeting experiment first; this is a test priority, not a proven best-performing channel.</div>",unsafe_allow_html=True)
    options = pd.DataFrame([
        ["Better borrower targeting", "Campaign dates unreliable; no treatment/payment key", "Priority for a randomized, reversible pilot"],
        ["AI voice automation", "No controlled comparison or verified RPC/outcome lineage", "Bounded pilot only after event identity repair"],
        ["Telephony infrastructure", "No reliable cost or uptime-to-payment link", "Defer scale decision; instrument uptime and call outcomes"],
        ["More collection agents", "Agent identities and productive-hour measures unreliable", "Do not scale headcount from current agent metrics"],
        ["WhatsApp / digital", "Event sequences and account mappings inconsistent", "Repair delivery/read/reply event model first"],
        ["Field operations", "Visit outcomes not reliably linked to settled payments or cost", "Measure incremental net recovery per visit first"],
    ], columns=["Investment option", "Evidence gap", "Decision posture"])
    st.dataframe(options,use_container_width=True,hide_index=True)
    st.markdown("**Proposed 6–8 week randomized pilot**")
    steps = [
        "Define the eligible account universe and freeze pre-period covariates.",
        "Randomize eligible accounts within DPD × risk × loan-type strata into current-strategy holdout and treatment.",
        "Persist assignment ID, actual exposure, timestamp, channel/vendor cost, complaints and settled payment events.",
        "Use intention-to-treat as the primary estimate; report incremental net recovery per eligible account.",
        "Release capital in stages only if the pre-agreed hurdle and customer safeguards are met."
    ]
    for i, item in enumerate(steps,1): st.markdown(f"**{i}.** {item}")
    st.markdown("**Economics to calculate after the pilot**")
    st.latex(r"\text{Incremental Net Recovery}=\text{Treatment Net Recovery}-\text{Holdout Net Recovery}")
    st.latex(r"\text{ROI}=\frac{\text{Incremental Net Recovery}-\text{Investment Cost}}{\text{Investment Cost}}")
    st.caption("No numerical ROI, incremental recovery forecast or break-even month is displayed: the supplied extracts do not contain unit costs, investment quotes or causal lift.")

st.markdown("---")
st.markdown("<div style='display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;color:#7A899B;font-size:.72rem'><span>◈ CREDRESOLVE · COLLECTIONS INTELLIGENCE</span><span>Prepared by Aditya Dwivedi · Decision support, not causal attribution</span></div>",unsafe_allow_html=True)

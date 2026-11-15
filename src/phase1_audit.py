"""
Collections Analytics — Phase 1 profiling and identity audit
Usage:
  python src/phase1_audit.py --data-dir ../collections_work --output-dir ../outputs
Requires: pandas, numpy, matplotlib
"""
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

KEYS = {
    "account_status_history":"history_id", "accounts":"account_id",
    "agent_sessions":"session_id", "agents":"agent_id", "borrowers":"borrower_id",
    "call_attempts":"attempt_id", "call_dispositions":"disposition_id",
    "calls":"call_id", "campaigns":"campaign_id", "complaints":"complaint_id",
    "daily_targeting":"target_id", "field_visits":"visit_id", "payments":"payment_id",
    "promises_to_pay":"ptp_id", "sms_events":"sms_event_id",
    "whatsapp_events":"whatsapp_event_id", "vendor_telephony":"vendor_id"
}

def main(data_dir, output_dir):
    data_dir, output_dir = Path(data_dir), Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    frames = {p.stem: pd.read_csv(p) for p in data_dir.glob("*.csv")}
    inventory, keys = [], []
    for name, df in frames.items():
        inventory.append({"dataset":name, "rows":len(df), "columns":len(df.columns),
                          "missing_cells":int(df.isna().sum().sum())})
    for name, key in KEYS.items():
        if name not in frames: continue
        df = frames[name]
        keys.append({"dataset":name, "candidate_key":key, "rows":len(df),
                     "unique_key_values":df[key].nunique(dropna=True),
                     "missing_key_values":int(df[key].isna().sum()),
                     "repeated_key_rows":int(df[key].duplicated().sum())})
    pd.DataFrame(inventory).to_csv(output_dir/"dataset_inventory.csv", index=False)
    pd.DataFrame(keys).to_csv(output_dir/"candidate_key_profile.csv", index=False)

    b = frames["borrowers"].groupby("borrower_id").agg(
        records=("borrower_id","size"), distinct_names=("name","nunique"),
        distinct_phones=("phone","nunique"), distinct_emails=("email","nunique")).reset_index()
    a = frames["agents"].groupby("agent_id").agg(
        records=("agent_id","size"), distinct_names=("agent_name","nunique"),
        distinct_employee_codes=("employee_code","nunique"),
        distinct_vendors=("vendor_id","nunique")).reset_index()
    b.to_csv(output_dir/"borrower_identity_profile.csv", index=False)
    a.to_csv(output_dir/"agent_identity_profile.csv", index=False)

    account_map = frames["accounts"][["account_id","borrower_id"]].dropna().drop_duplicates()
    rel = []
    for t in ["payments","calls","call_attempts","whatsapp_events","sms_events",
              "field_visits","promises_to_pay","complaints","account_status_history"]:
        d = frames[t][["account_id","borrower_id"]].dropna().drop_duplicates()
        m = d.merge(account_map, on="account_id", how="left", suffixes=("_event","_account"), indicator=True)
        matched = m["_merge"].eq("both")
        mismatch = matched & (m["borrower_id_event"] != m["borrower_id_account"])
        rel.append({"event_dataset":t, "distinct_pairs":len(d),
                    "account_not_found":int((~matched).sum()),
                    "borrower_mismatch":int(mismatch.sum()),
                    "mismatch_pct_of_matched":round(mismatch.sum()/matched.sum()*100,2) if matched.sum() else np.nan})
    pd.DataFrame(rel).to_csv(output_dir/"account_borrower_relationship_audit.csv", index=False)

    fig, ax = plt.subplots(1,2,figsize=(13,5))
    b[["distinct_names","distinct_phones","distinct_emails"]].gt(1).sum().plot(kind="bar",ax=ax[0],title="Borrower ID conflicts")
    a[["distinct_names","distinct_employee_codes","distinct_vendors"]].gt(1).sum().plot(kind="bar",ax=ax[1],title="Agent ID conflicts")
    plt.tight_layout()
    fig.savefig(output_dir/"identity_conflicts.png",dpi=160,bbox_inches="tight")
    plt.close(fig)
    print("Audit complete. Outputs saved to", output_dir)

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--data-dir", required=True)
    p.add_argument("--output-dir", required=True)
    args=p.parse_args()
    main(args.data_dir,args.output_dir)

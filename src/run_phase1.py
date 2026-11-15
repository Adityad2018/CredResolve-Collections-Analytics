from pathlib import Path
import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "outputs"
VIS = ROOT / "visualizations"
DB = ROOT / "data" / "processed" / "collections.db"
OUT.mkdir(exist_ok=True)
VIS.mkdir(exist_ok=True)
DB.parent.mkdir(parents=True, exist_ok=True)

KEYS = {
    "account_status_history":"history_id", "accounts":"account_id",
    "agent_sessions":"session_id", "agents":"agent_id", "borrowers":"borrower_id",
    "call_attempts":"attempt_id", "call_dispositions":"disposition_id",
    "calls":"call_id", "campaigns":"campaign_id", "complaints":"complaint_id",
    "daily_targeting":"target_id", "field_visits":"visit_id", "payments":"payment_id",
    "promises_to_pay":"ptp_id", "sms_events":"sms_event_id",
    "whatsapp_events":"whatsapp_event_id", "vendor_telephony":"vendor_id"
}
EVENT_TABLES = [
    "payments","calls","call_attempts","whatsapp_events","sms_events",
    "field_visits","promises_to_pay","complaints","account_status_history","call_dispositions"
]

def main():
    files = sorted(RAW.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSV files found in {RAW}. Place source CSVs in data/raw.")

    frames = {p.stem: pd.read_csv(p) for p in files}
    print(f"Loaded {len(frames)} CSV files from {RAW}")

    # Load every source CSV to SQLite. Table names are source filenames.
    with sqlite3.connect(DB) as con:
        for name, df in frames.items():
            df.to_sql(name, con, if_exists="replace", index=False)
    print(f"SQLite database created: {DB}")

    inventory = pd.DataFrame([
        {"dataset": n, "rows": len(df), "columns": len(df.columns),
         "missing_cells": int(df.isna().sum().sum()),
         "missing_pct": round(df.isna().sum().sum()/(df.shape[0]*df.shape[1])*100, 2) if df.size else 0}
        for n, df in frames.items()
    ]).sort_values("rows", ascending=False)
    inventory.to_csv(OUT/"dataset_inventory.csv", index=False)

    key_rows = []
    for table, key in KEYS.items():
        if table not in frames or key not in frames[table].columns:
            continue
        df = frames[table]
        key_rows.append({
            "dataset": table, "candidate_key": key, "rows": len(df),
            "unique_key_values": int(df[key].nunique(dropna=True)),
            "missing_key_values": int(df[key].isna().sum()),
            "repeated_key_rows": int(df[key].duplicated().sum()),
            "duplicate_key_groups": int(df.loc[df[key].duplicated(keep=False), key].nunique())
        })
    key_profile = pd.DataFrame(key_rows).sort_values("repeated_key_rows", ascending=False)
    key_profile.to_csv(OUT/"candidate_key_profile.csv", index=False)

    # Entity identity profiles
    borrower = frames["borrowers"]
    borrower_profile = borrower.groupby("borrower_id", dropna=False).agg(
        records=("borrower_id","size"), distinct_names=("name","nunique"),
        distinct_phones=("phone","nunique"), distinct_emails=("email","nunique"),
        distinct_cities=("city","nunique"), distinct_states=("state","nunique")
    ).reset_index()
    borrower_profile.to_csv(OUT/"borrower_identity_profile.csv", index=False)

    agents = frames["agents"]
    agent_profile = agents.groupby("agent_id", dropna=False).agg(
        records=("agent_id","size"), distinct_names=("agent_name","nunique"),
        distinct_employee_codes=("employee_code","nunique"),
        distinct_vendors=("vendor_id","nunique"), distinct_teams=("team","nunique")
    ).reset_index()
    agent_profile.to_csv(OUT/"agent_identity_profile.csv", index=False)

    # Relationship audit against accounts master
    account_map = frames["accounts"][["account_id","borrower_id"]].dropna().drop_duplicates()
    relationship = []
    for table in EVENT_TABLES:
        if table not in frames:
            continue
        df = frames[table]
        if not {"account_id","borrower_id"}.issubset(df.columns):
            continue
        pairs = df[["account_id","borrower_id"]].dropna().drop_duplicates()
        merged = pairs.merge(account_map, on="account_id", how="left",
                             suffixes=("_event","_account"), indicator=True)
        matched = merged["_merge"].eq("both")
        mismatch = matched & (merged["borrower_id_event"] != merged["borrower_id_account"])
        relationship.append({
            "event_dataset": table, "distinct_account_borrower_pairs": len(pairs),
            "pairs_with_account_match": int(matched.sum()),
            "pairs_without_account_match": int((~matched).sum()),
            "matched_pairs_with_borrower_mismatch": int(mismatch.sum()),
            "mismatch_pct_of_matched": round(mismatch.sum()/matched.sum()*100, 2) if matched.sum() else np.nan
        })
    relationship = pd.DataFrame(relationship)
    relationship.to_csv(OUT/"account_borrower_relationship_audit.csv", index=False)

    # Visual 1: row counts across all source tables
    fig, ax = plt.subplots(figsize=(11, 7))
    top = inventory.sort_values("rows").tail(18)
    ax.barh(top["dataset"], top["rows"])
    ax.set_title("Collections dataset — source table row counts")
    ax.set_xlabel("Rows")
    fig.tight_layout()
    fig.savefig(VIS/"dataset_row_counts.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # Visual 2: identity conflicts
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    borrower_conf = (borrower_profile[["distinct_names","distinct_phones","distinct_emails"]] > 1).sum()
    borrower_conf.plot(kind="bar", ax=axes[0], title="Borrower IDs with conflicting attributes")
    agent_conf = (agent_profile[["distinct_names","distinct_employee_codes","distinct_vendors"]] > 1).sum()
    agent_conf.plot(kind="bar", ax=axes[1], title="Agent IDs with conflicting attributes")
    fig.tight_layout()
    fig.savefig(VIS/"identity_conflicts.png", dpi=160, bbox_inches="tight")
    plt.close(fig)

    # Visual 3: account relationship mismatches
    if not relationship.empty:
        fig, ax = plt.subplots(figsize=(11, 6))
        chart = relationship.sort_values("mismatch_pct_of_matched")
        ax.barh(chart["event_dataset"], chart["mismatch_pct_of_matched"])
        ax.set_xlabel("Mismatch among matched account pairs (%)")
        ax.set_title("Account-to-borrower relationship audit")
        ax.set_xlim(0, 105)
        fig.tight_layout()
        fig.savefig(VIS/"account_borrower_mismatch.png", dpi=160, bbox_inches="tight")
        plt.close(fig)

    # Export compact findings summary
    summary = {
        "source_csv_files": len(files),
        "borrower_rows": len(borrower),
        "distinct_borrower_ids": int(borrower["borrower_id"].nunique()),
        "borrower_ids_multiple_names": int((borrower_profile["distinct_names"] > 1).sum()),
        "agent_rows": len(agents),
        "distinct_agent_ids": int(agents["agent_id"].nunique()),
        "agent_ids_multiple_names": int((agent_profile["distinct_names"] > 1).sum()),
        "account_rows": len(frames["accounts"]),
        "distinct_account_ids": int(frames["accounts"]["account_id"].nunique()),
        "payment_rows": len(frames["payments"]),
        "distinct_payment_ids": int(frames["payments"]["payment_id"].nunique())
    }
    pd.Series(summary, name="value").to_csv(OUT/"phase1_summary.csv", header=True)
    print("\nPHASE 1 COMPLETE")
    print(pd.Series(summary).to_string())
    print(f"\nOutputs: {OUT}")
    print(f"Visualizations: {VIS}")
    print(f"Database: {DB}")

if __name__ == "__main__":
    main()

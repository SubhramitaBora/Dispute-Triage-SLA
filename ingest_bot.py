# ingest_bot.py
import os
import json
import shutil
import re
from datetime import datetime
from typing import Optional

import pandas as pd
from apscheduler.schedulers.background import BackgroundScheduler

# unified engines (single source of truth)
from engines.priority_engine import compute_priority
from engines.clustering_engine import SimpleClusterer

# ------------------------------
# Configuration / paths
# ------------------------------
INCOMING_DIR = "incoming"
PROCESSED_DIR = "processed"
DB_FILE = "static/disputes.json"

os.makedirs(INCOMING_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)
os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)

# ------------------------------
# Engines / helpers
# ------------------------------
clusterer = SimpleClusterer()

# mapping for free-text issue categories -> short code (extend if needed)
CATEGORY_MAP = {
    "amount deducted but not credited to beneficiary": "not_credited",
    "amount deducted - time out": "timeout",
    "reversal initiated but credit to source not received": "reversal_not_reflecting",
    "wrong beneficiary": "wrong_beneficiary",
    "transaction not initiated by the customer": "fraud",
}

def normalize_issue(val: Optional[str]) -> str:
    if not isinstance(val, str):
        return "other"
    s = val.replace("\xa0", " ").strip().lower()
    return CATEGORY_MAP.get(s, s)

def normalize_channel(ch: Optional[str]) -> str:
    if not isinstance(ch, str):
        return str(ch or "").strip().lower()
    return ch.strip().lower()

def extract_stage(value) -> int:
    """Accept 'Stage 3', '3', 3 -> return int stage, fallback 1"""
    if value is None:
        return 1
    try:
        if isinstance(value, (int, float)):
            return int(value)
    except Exception:
        pass
    try:
        s = str(value)
        m = re.search(r"(\d+)", s)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return 1

def safe_to_float(x) -> float:
    try:
        if pd.isna(x):
            return 0.0
    except Exception:
        pass
    try:
        s = str(x).replace(",", "").strip()
        return float(s) if s != "" else 0.0
    except Exception:
        return 0.0

def safe_to_int(x) -> int:
    try:
        if pd.isna(x):
            return 0
    except Exception:
        pass
    try:
        s = str(x).split(".")[0].replace(",", "").strip()
        return int(s) if s != "" else 0
    except Exception:
        return 0

# ------------------------------
# DB helpers
# ------------------------------
def load_disputes():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def save_disputes(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ------------------------------
# Excel processing
# ------------------------------
def process_excel_file(filepath: str) -> bool:
    print(f"[{datetime.now().isoformat()}] Processing: {filepath}")
    try:
        df = pd.read_excel(filepath, engine="openpyxl")
    except Exception as e:
        print("❌ Failed to read Excel:", e)
        return False

    # normalize column names
    col_map = {
        "s.no.": "S.No.",
        "s.no": "S.No.",
        "sno": "S.No.",
        "ticket id": "Ticket ID",
        "ticket": "Ticket ID",
        "channel": "Channel",
        "amount (in inr)": "Amount (in INR)",
        "amount(in inr)": "Amount (in INR)",
        "amount (inr)": "Amount (in INR)",
        "amount": "Amount (in INR)",
        "days open": "Days Open",
        "issue category": "Issue Category",
        "complaint type": "Issue Category",
        "present stage": "Present Stage",
        "stage": "Stage",
        "days in present stage": "Days in Present Stage",
        "days in present_stage": "Days in Present Stage",
        "status": "Status",
        "sla priority": "SLA Priority",
    }

    clean_cols = []
    for col in df.columns:
        if not isinstance(col, str):
            clean_cols.append(str(col))
            continue
        c = col.replace("\xa0", " ").strip().lower()
        clean_cols.append(col_map.get(c, col))
    df.columns = clean_cols

    required = [
        "S.No.",
        "Ticket ID",
        "Channel",
        "Amount (in INR)",
        "Days Open",
        "Issue Category",
        "Stage",
    ]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print("❌ Missing columns:", missing)
        return False

    existing = load_disputes()
    existing_by_id = {d.get("id"): d for d in existing}

    for _, row in df.iterrows():
        raw_ticket = row.get("Ticket ID")
        if pd.isna(raw_ticket) or raw_ticket is None:
            # skip blank ticket ids
            ticket_id = None
        else:
            ticket_id = str(raw_ticket).strip()

        if not ticket_id:
            # generate fallback id (shouldn't normally happen for your sheet)
            ticket_id = f"UX{int(datetime.now().timestamp())}_{_}"

        channel = normalize_channel(row.get("Channel"))
        amount = safe_to_float(row.get("Amount (in INR)"))
        days_open = safe_to_int(row.get("Days Open"))
        stage = extract_stage(row.get("Stage"))
        days_in_present_stage = safe_to_int(row.get("Days in Present Stage"))
        complaint_type = normalize_issue(row.get("Issue Category", ""))

        # compute via unified engine
        scores = compute_priority(amount, complaint_type, channel, stage, days_open)
        # cluster using existing SimpleClusterer.assign(...) signature
        # pass merchant_id and txn_time_iso if present in sheet (not required)
        merchant = row.get("Merchant ID") if "Merchant ID" in df.columns else None
        txn_time = row.get("Txn Time ISO") if "Txn Time ISO" in df.columns else None
        cluster_id = clusterer.assign(merchant, complaint_type, txn_time, case_id=ticket_id)
        
        # ------------------------------
# Determine correct business team
# ------------------------------
        ct = complaint_type

        if ct == "fraud":
            team = "Fraud Investigation Team"
        elif ct == "wrong_beneficiary":
            team = "Settlement Team"
        elif ct in ("reversal_not_reflecting", "reversal_initiated"):
            team = "Reversal Processing Team"
        elif ct in ("timeout", "technical_issue"):
            team = "Technical Operations"
        elif ct == "not_credited":
            team = "Settlement Queue"
        else:
            team = "General Dispute Desk"
        

        # Build normalized record (matches other files)
        record = {
            "id": ticket_id,
            "ticket_id": ticket_id,
            "merchant_id": merchant,
            "channel": channel.upper() if channel else channel,
            "amount": amount,
            "days_open": days_open,
            "complaint_type": complaint_type,
            "present_stage": row.get("Present Stage"),
            "stage": int(stage),
            "days_in_present_stage": int(days_in_present_stage or 0),
            "status": row.get("Status"),
            # scores & priority fields from unified engine
            **scores,
            "cluster_id": cluster_id,
             "route_to_team": team,
            "ingested_at": datetime.now().isoformat()
        }

        existing_by_id[record["id"]] = record

    all_records = list(existing_by_id.values())
    save_disputes(all_records)
    print(f"✅ Ingested {len(df)} rows from {os.path.basename(filepath)}")
    return True

# ------------------------------
# Ingest job (scans incoming folder)
# ------------------------------
def ingest_job():
    try:
        files = sorted([f for f in os.listdir(INCOMING_DIR) if f.lower().endswith((".xlsx", ".xls"))])
    except Exception as e:
        print("❌ Could not list incoming folder:", e)
        return

    if not files:
        return

    for fn in files:
        if fn.startswith("~$"):
            continue
        full = os.path.join(INCOMING_DIR, fn)
        print(f"[{datetime.now().isoformat()}] Found file: {full}")
        ok = process_excel_file(full)
        if ok:
            dest_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}__{fn}"
            dest = os.path.join(PROCESSED_DIR, dest_name)
            try:
                shutil.move(full, dest)
                print(f"➡ Moved {fn} → processed/{dest_name}")
            except Exception as e:
                print("❌ Failed to move processed file:", e)

# ------------------------------
# scheduler wrapper
# ------------------------------
_scheduler = None

def start_ingest_bot(interval_seconds: int = 30):
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler()
    _scheduler.add_job(ingest_job, "interval", seconds=interval_seconds, next_run_time=datetime.now())
    _scheduler.start()
    print(f"📥 Ingest Bot Started (every {interval_seconds}s). Folder: {os.path.abspath(INCOMING_DIR)}")
    return _scheduler

# manual run
if __name__ == "__main__":
    print("Manual run: processing existing files in incoming/")
    ingest_job()

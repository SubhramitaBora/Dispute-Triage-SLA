# main.py
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import json
import os
from datetime import datetime

from models import DisputeRequest, DisputeResponse
from engines.priority_engine import compute_priority
from engines.clustering_engine import SimpleClusterer
from ingest_bot import start_ingest_bot
from bot import start_sla_bot

app = FastAPI(title="Unified Priority Engine API")
app.mount("/static", StaticFiles(directory="static"), name="static")

clusterer = SimpleClusterer()

DB_FILE = "static/disputes.json"
os.makedirs("static", exist_ok=True)

@app.get("/")
def root():
    return FileResponse("dashboard.html")


def load_disputes():
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_disputes(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)


@app.post("/score_dispute", response_model=DisputeResponse)
def score_dispute(req: DisputeRequest):

    # ---- Compute everything from unified engine ----
    scores = compute_priority(
        req.amount,
        req.complaint_type,
        req.channel,
        req.stage,
        req.days_open
    )
    
     # ---- Determine correct team ----
    ct = req.complaint_type.lower()

    if ct == "fraud":
        team = "Fraud Investigation Team"
    elif ct == "wrong_beneficiary":
        team = "Settlement Team"
    elif ct in ["reversal_not_reflecting", "reversal_initiated"]:
        team = "Reversal Processing Team"
    elif ct in ["timeout", "technical_issue"]:
        team = "Technical Ops"
    elif ct == "not_credited":
        team = "Settlement Queue"
    else:
        team = "General Dispute Desk"

    # ---- Clustering ----
    cluster_id = clusterer.assign(
        req.merchant_id,
        req.complaint_type,
        req.txn_time_iso
    )

    rec = {
        "id": req.merchant_id or f"AUTO_{datetime.now().timestamp()}",
        "merchant_id": req.merchant_id,
        "channel": req.channel,
        "amount": req.amount,
        "days_open": req.days_open,
        "complaint_type": req.complaint_type,
        "stage": req.stage,

        **scores,

        "cluster_id": cluster_id,
        "ingested_at": "manual_api"
    }

    data = load_disputes()
    data.append(rec)
    save_disputes(data)

    return DisputeResponse(
        **scores,
       route_to_team=team,
        cluster_id=cluster_id
    )


@app.on_event("startup")
def on_start():
    start_sla_bot()
    start_ingest_bot()
    print("🚀 Priority Engine + SLA Bot + Ingest Bot Running")


@app.get("/dashboard")
def dashboard():
    return FileResponse("dashboard.html")

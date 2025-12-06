# bot.py
from apscheduler.schedulers.background import BackgroundScheduler
import json
from datetime import datetime

from engines.priority_engine import compute_priority
from engines.clustering_engine import SimpleClusterer

DB_FILE = "static/disputes.json"
clusterer = SimpleClusterer()

def load_disputes():
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_disputes(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def sla_countdown_job():
    print(f"[{datetime.now()}] SLA Countdown Running...")

    disputes = load_disputes()
    updated = []

    for d in disputes:
        d["days_open"] = int(d.get("days_open", 0)) + 1

        # ---- Recompute EVERYTHING using core engine ----
        scores = compute_priority(
            d.get("amount", 0),
            d.get("complaint_type", "other"),
            d.get("channel", "other"),
            d.get("stage", 1),
            d["days_open"]
        )

        d.update(scores)

        updated.append(d)

    save_disputes(updated)
    print("SLA Update Cycle Complete.\n")


def start_sla_bot(interval_minutes=1440):  # 24 hours
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        sla_countdown_job,
        "interval",
        minutes=interval_minutes,
        next_run_time=datetime.now()
    )
    scheduler.start()
    print(f"⏳ SLA Bot started (every {interval_minutes} min)")
    return scheduler

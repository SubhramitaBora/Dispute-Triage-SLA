# engines/priority_engine.py

from .impact_engine import compute_impact
from .stage_engine import StageStuckEngine
from .sla_engine import compute_sla

stage_engine = StageStuckEngine()

def compute_priority(amount, complaint_type, channel, stage, days_open):

    impact = compute_impact(amount, complaint_type, channel)
    weight, stage_score = stage_engine.compute(stage, days_open)
    sla_vals = compute_sla(days_open)

    total = impact["impact_score"] + stage_score + sla_vals["sla_score"]

    if total >= 30:
        priority = "L0"
    elif total >= 20:
        priority = "L1"
    elif total >= 12:
        priority = "L2"
    else:
        priority = "L3"

    return {
        **impact,
        "weight": weight,
        "stage_score": stage_score,
        **sla_vals,
        "total_priority_score": total,
        "recommended_priority": priority
    }

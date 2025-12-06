# engines/sla_engine.py

def sla_level(days_open: int) -> str:
    if days_open <= 3:
        return "L3"
    if days_open <= 11:
        return "L2"
    if days_open <= 25:
        return "L1"
    return "L0"

def sla_score(level: str) -> int:
    mapping = {"L3": 1, "L2": 3, "L1": 6, "L0": 10}
    return mapping.get(level, 1)

def compute_sla(days_open: int):
    lvl = sla_level(days_open)
    scr = sla_score(lvl)
    return {
        "sla_level": lvl,
        "sla_score": scr
    }

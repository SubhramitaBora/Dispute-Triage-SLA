# engines/impact_engine.py

def amount_score(amount: float) -> int:
    if amount > 100000:
        return 8
    if amount > 50000:
        return 6
    if amount > 10000:
        return 4
    if amount > 1000:
        return 2
    return 1

def type_score(complaint_type: str) -> int:
    mapping = {
        "fraud": 10,
        "wrong_beneficiary": 8,
        "reversal_not_reflecting": 7,
        "not_credited": 7,
        "reversal_initiated": 6,
        "timeout": 4,
        "technical_issue": 2,
        "other": 1
    }
    return mapping.get(complaint_type.lower(), 1)

def channel_score(channel: str) -> int:
    mapping = {
        "upi": 4,
        "card": 3,
        "card_domestic": 3,
        "card_international": 5,
        "atm": 3,
        "app": 4,
        "web": 3,
        "branch": 2
    }
    return mapping.get(channel.lower(), 1)

def compute_impact(amount, complaint_type, channel):
    a = amount_score(amount)
    t = type_score(complaint_type)
    c = channel_score(channel)
    return {
        "amount_score": a,
        "type_score": t,
        "channel_score": c,
        "impact_score": a + t + c
    }

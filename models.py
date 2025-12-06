from pydantic import BaseModel, Field
from typing import Optional

# ============================================================
# INPUT MODEL (API → Scoring Engine)
# ============================================================
class DisputeRequest(BaseModel):
    amount: float = Field(..., example=15000)

    # Accepts Excel long labels OR internal short codes
    complaint_type: str = Field(
        ..., 
        example="wrong_beneficiary",
        description="Complaint category converted to short code"
    )

    channel: str = Field(
        ..., 
        example="upi",
        description="Transaction channel"
    )

    # Stage number used by Stage-Stuck Engine
    stage: int = Field(
        ..., 
        ge=1, le=5, 
        example=3,
        description="Internal stage number"
    )

    # Used by Stage Engine + SLA Engine
    days_open: int = Field(
        ..., 
        ge=0, 
        example=12
    )

    # Optional metadata for clustering
    merchant_id: Optional[str] = Field(None, example="MERCH_123")
    customer_id: Optional[str] = Field(None, example="CUST_456")

    # Used by Smart Clustering Engine
    txn_time_iso: Optional[str] = Field(
        None, 
        example="2025-11-26T10:12:00",
        description="ISO timestamp used for cluster grouping"
    )


# ============================================================
# OUTPUT MODEL (Response from Scoring API)
# ============================================================
class DisputeResponse(BaseModel):

    # IMPACT SCORES
    impact_score: int
    amount_score: int
    type_score: int
    channel_score: int

    # STAGE STUCK ENGINE
    stage_score: int
    weight: int      # stage weight

    # SLA METRICS
    sla_level: str
    sla_score: int

    # FINAL PRIORITY SCORE
    total_priority_score: int
    recommended_priority: str

    # TEAM ROUTING
    route_to_team: str

    # CLUSTER ID (optional)
    cluster_id: Optional[str] = None

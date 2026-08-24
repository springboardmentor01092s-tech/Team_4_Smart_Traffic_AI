import uuid
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class InsightType(str, Enum):
    """Categorizes the nature of the AI traffic insight."""
    PREDICTIVE_WARNING = "PREDICTIVE_WARNING"
    REROUTE_RECOMMENDATION = "REROUTE_RECOMMENDATION"
    CONGESTION_RISK = "CONGESTION_RISK"
    TRAFFIC_TREND = "TRAFFIC_TREND"
    INCIDENT_RISK = "INCIDENT_RISK"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"

class RiskLevel(str, Enum):
    """Indicates the overall risk level of the insight."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class TrafficInsightRead(BaseModel):
    """Structured insight and recommendation for a traffic segment."""
    segment_id: uuid.UUID
    insight_type: InsightType
    risk_level: RiskLevel
    title: str
    recommendation: str
    evidence: list[str] = Field(default_factory=list)
    generated_at: datetime

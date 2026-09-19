from pydantic import BaseModel, Field
from enum import Enum

class TicketCategory(str, Enum):
  BILLING = "billing"
  TECHNICAL = "technical"
  ACCOUNT = "account"
  FEATURE_REQUEST = "feature_request"
  OTHER = "other"

class UrgencyLevel(str, Enum):
  LOW = "low"
  MEDIUM = "medium"
  HIGH = "high"
  CRITICAL = "critical"

class IncomingTicket(BaseModel):
  ticket_id: str
  customer_id: str
  subject: str
  body: str

class TriageResult(BaseModel):
  category: TicketCategory
  urgency: UrgencyLevel
  can_auto_resolve: bool
  confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score between 0 and 1")
  reasoning: str

class TicketResolution(BaseModel):
  ticket_id: str
  triage: TriageResult
  suggested_response: str | None = None
  escalate_to_human: bool = False
  relevant_kb_articles: list[str] = Field(default_factory=list, description="List of relevant knowledge base articles")



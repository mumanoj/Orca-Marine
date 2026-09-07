from datetime import datetime, timezone
from typing import Optional, Any

try:
    from beanie import Document, Indexed
    HAS_BEANIE = True
except ImportError:
    HAS_BEANIE = False
    from pydantic import BaseModel as Document # type: ignore
    def Indexed(t, unique=False): return t # type: ignore

class ConversationDocument(Document): # type: ignore
    conversation_id: Indexed(str, unique=True) # type: ignore
    created_at: datetime = datetime.now(timezone.utc)
    updated_at: datetime = datetime.now(timezone.utc)
    language: str = "en"
    last_latitude: float = 12.91
    last_longitude: float = 74.85

    if HAS_BEANIE:
        class Settings:
            name = "conversations"


class MessageDocument(Document): # type: ignore
    conversation_id: Indexed(str) # type: ignore
    role: str  # "user" or "assistant"
    query: str
    execution_mode: str = "C"
    recommendation: Optional[str] = None
    safety_rating: Optional[str] = None
    deterministic_score: Optional[int] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    explainability_factors: Optional[list[dict[str, Any]]] = None
    evidence: Optional[list[dict[str, Any]]] = None
    warnings: Optional[list[str]] = None
    agents_executed: Optional[list[str]] = None
    tools_executed: Optional[list[str]] = None
    created_at: datetime = datetime.now(timezone.utc)

    if HAS_BEANIE:
        class Settings:
            name = "messages"


class ExecutionTraceDocument(Document): # type: ignore
    conversation_id: Indexed(str) # type: ignore
    trace_events: list[dict[str, Any]] = []
    execution_duration: float = 0.0
    created_at: datetime = datetime.now(timezone.utc)

    if HAS_BEANIE:
        class Settings:
            name = "execution_traces"

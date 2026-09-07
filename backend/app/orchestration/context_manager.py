"""
ORCA Session & Conversation Context Manager.
Provides deterministic multi-turn conversation state persistence and context merging.
Maintains user location, selected fishing zone, last intent, and time windows across chat turns.
"""
import logging
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ResolvedContext(BaseModel):
    conversation_id: str
    latitude: float = 12.91
    longitude: float = 74.85
    location_name: Optional[str] = "Mangalore"
    selected_zone: Optional[Dict[str, Any]] = None
    last_query: Optional[str] = None
    last_intent_type: Optional[str] = None
    last_query_results_summary: Optional[str] = None
    time_window: Optional[Dict[str, Any]] = None


class SessionContextManager:
    """
    Manages persistent conversation context per conversation_id.
    """

    def __init__(self):
        self._sessions: Dict[str, ResolvedContext] = {}

    def get_or_create_session(self, conversation_id: str) -> ResolvedContext:
        if not conversation_id:
            conversation_id = "default_session"
        if conversation_id not in self._sessions:
            self._sessions[conversation_id] = ResolvedContext(
                conversation_id=conversation_id,
                latitude=12.91,
                longitude=74.85,
                location_name="Mangalore"
            )
        return self._sessions[conversation_id]

    def reset_session(self, conversation_id: str) -> ResolvedContext:
        """Completely clears conversation state when user clicks NEW CHAT."""
        new_session = ResolvedContext(
            conversation_id=conversation_id,
            latitude=0.0,
            longitude=0.0,
            location_name=None,
            selected_zone=None,
            last_query=None,
            last_intent_type=None,
            last_query_results_summary=None,
            time_window=None
        )
        self._sessions[conversation_id] = new_session
        logger.info(f"Conversation context reset for conversation_id='{conversation_id}'.")
        return new_session

    def update_after_query(
        self,
        conversation_id: str,
        query: str,
        latitude: float,
        longitude: float,
        location_name: Optional[str],
        selected_zone: Optional[Dict[str, Any]],
        intent_type: str,
        summary: Optional[str]
    ) -> ResolvedContext:
        session = self.get_or_create_session(conversation_id)
        session.last_query = query
        session.last_intent_type = intent_type
        if latitude != 0.0 and longitude != 0.0:
            session.latitude = latitude
            session.longitude = longitude
        if location_name:
            session.location_name = location_name
        if selected_zone:
            session.selected_zone = selected_zone
        if summary:
            session.last_query_results_summary = summary
        return session

session_context_manager = SessionContextManager()

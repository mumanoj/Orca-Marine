import logging
from datetime import datetime, timezone
from typing import Optional, Any
from fastapi import APIRouter, HTTPException

from app.schemas.query import QueryRequest, MarineQueryResult
from app.orchestration.orchestrator import orchestrator
from app.core.config import settings
from app.core.llm.manager import llm_manager
from app.db import is_db_connected
from app.db_models import ConversationDocument, MessageDocument, ExecutionTraceDocument

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory fallback conversation cache for when MongoDB is disconnected
_memory_conversations: dict[str, list[dict[str, Any]]] = {}

from app.orchestration.context_manager import session_context_manager

@router.post("/query", response_model=MarineQueryResult)
async def query_orca(request: QueryRequest):
    """
    POST endpoint to process a marine intelligence query with multi-turn conversation memory,
    grounded explainability factors, and MongoDB persistence (or graceful fallback).
    """
    try:
        if not getattr(request, "mode", None):
            request.mode = "autonomous"
            
        conv_id = request.conversation_id or f"session_{int(datetime.now(timezone.utc).timestamp())}"
        request.conversation_id = conv_id

        # Check for explicit NEW CHAT reset
        if getattr(request, "reset", False):
            session_ctx = session_context_manager.reset_session(conv_id)
            if is_db_connected():
                try:
                    await MessageDocument.find(MessageDocument.conversation_id == conv_id).delete()
                except Exception:
                    pass
            _memory_conversations[conv_id] = []
        else:
            session_ctx = session_context_manager.get_or_create_session(conv_id)

        # Multi-turn Conversational Context Retrieval & Location Inheritance
        if not getattr(request, "reset", False):
            if request.latitude != 0.0 or request.longitude != 0.0:
                session_ctx.latitude = request.latitude
                session_ctx.longitude = request.longitude
            else:
                request.latitude = session_ctx.latitude
                request.longitude = session_ctx.longitude

        # Websocket trace streaming callback
        async def ws_callback(event_type: str, data: dict):
            from app.routes.websocket import stream_trace_event
            await stream_trace_event(conv_id, event_type, data)
            
        # Execute query through Orchestrator
        result = await orchestrator.execute(request, event_callback=ws_callback)

        # Update persistent session context with query outcomes & selected zone
        pfz_ev = next((e for e in result.evidence if e.parameter == "nearest_potential_fishing_zone"), None)
        selected_zone_info = pfz_ev.value if (pfz_ev and isinstance(pfz_ev.value, dict)) else None
        session_context_manager.update_after_query(
            conversation_id=conv_id,
            query=request.query,
            latitude=request.latitude,
            longitude=request.longitude,
            location_name=None,
            selected_zone=selected_zone_info,
            intent_type=result.decision_summary.get("query_semantics", "NEAREST_ZONE"),
            summary=result.recommendation
        )

        # Async non-blocking MongoDB Persistence
        persisted = False
        if is_db_connected():
            try:
                # 1. Update/Create Conversation Document
                conv_doc = await ConversationDocument.find_one(ConversationDocument.conversation_id == conv_id)
                if not conv_doc:
                    conv_doc = ConversationDocument(
                        conversation_id=conv_id,
                        language=request.language,
                        last_latitude=request.latitude,
                        last_longitude=request.longitude
                    )
                else:
                    conv_doc.updated_at = datetime.now(timezone.utc)
                    conv_doc.last_latitude = request.latitude
                    conv_doc.last_longitude = request.longitude
                await conv_doc.save()

                # 2. Save User Message
                user_msg = MessageDocument(
                    conversation_id=conv_id,
                    role="user",
                    query=request.query,
                    execution_mode=getattr(request, "mode", "autonomous")
                )
                await user_msg.save()

                # 3. Save Assistant Outcome Message
                assistant_msg = MessageDocument(
                    conversation_id=conv_id,
                    role="assistant",
                    query=request.query,
                    execution_mode=getattr(request, "mode", "autonomous"),
                    recommendation=result.recommendation,
                    safety_rating=result.safety_rating,
                    deterministic_score=result.deterministic_score,
                    confidence=result.confidence,
                    explanation=result.explanation,
                    explainability_factors=result.explainability_factors,
                    evidence=[e.model_dump() for e in result.evidence],
                    warnings=result.warnings,
                    agents_executed=result.agents_executed,
                    tools_executed=result.tools_executed
                )
                await assistant_msg.save()
                persisted = True
                logger.info(f"Query outcome successfully persisted to MongoDB (conversation_id: {conv_id}).")

            except Exception as e:
                logger.warning(f"MongoDB persistence error ({e}). Query result returned via fallback.")
                persisted = False

        # In-memory fallback caching
        if conv_id not in _memory_conversations:
            _memory_conversations[conv_id] = []
        _memory_conversations[conv_id].append({"role": "user", "query": request.query})
        _memory_conversations[conv_id].append(result.model_dump())

        result.persisted = persisted
        logger.info(
            f"\n============================================================\n"
            f"[FINAL API RESPONSE DELIVERED TO FRONTEND]\n"
            f"Query: '{request.query}'\n"
            f"Primary Recommendation: '{result.recommendation}'\n"
            f"Explanation Summary: '{result.explanation[:120]}...'\n"
            f"============================================================"
        )
        return result

    except Exception as e:
        logger.error(f"Query processing exception: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Query execution failed: {str(e)}")


@router.get("/conversations/{conversation_id}")
async def get_conversation_history(conversation_id: str):
    """
    Retrieve message history thread for a specific conversation ID.
    """
    if is_db_connected():
        try:
            db_msgs = await MessageDocument.find(MessageDocument.conversation_id == conversation_id).sort("+created_at").to_list()
            return {
                "conversation_id": conversation_id,
                "source": "mongodb",
                "message_count": len(db_msgs),
                "messages": [m.model_dump() for m in db_msgs]
            }
        except Exception as e:
            logger.warning(f"Error fetching conversation history from MongoDB ({e}). Returning memory cache.")
            
    mem_msgs = _memory_conversations.get(conversation_id, [])
    return {
        "conversation_id": conversation_id,
        "source": "memory_cache",
        "message_count": len(mem_msgs),
        "messages": mem_msgs
    }

@router.get("/llm/status")
def get_llm_status():
    """
    Returns active state of API keys/LLM providers (Groq and Gemini).
    """
    active = llm_manager.get_active_providers()
    return {
        "primary_provider": settings.LLM_PRIMARY_PROVIDER,
        "secondary_provider": settings.LLM_SECONDARY_PROVIDER,
        "active_providers": active,
        "groq_configured": llm_manager.groq.is_available(),
        "gemini_configured": llm_manager.gemini.is_available()
    }

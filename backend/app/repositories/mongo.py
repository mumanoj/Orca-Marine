import asyncio
import logging
from typing import Optional
from app.repositories.interfaces import BaseStateRepository
from app.repositories.memory import InMemoryStateRepository
from app.schemas.query import MarineQueryResult
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoStateRepository(BaseStateRepository):
    """
    MongoDB Async Motor State Repository for persisting query traces, evidence, and session history.
    Falls back gracefully to InMemoryStateRepository if MongoDB is unreachable or unconfigured.
    """

    def __init__(self, mongodb_url: str = settings.MONGODB_URL, db_name: str = settings.MONGODB_DATABASE):
        self._memory_fallback = InMemoryStateRepository()
        self._db = None
        self._client = None

        if mongodb_url:
            try:
                import motor.motor_asyncio
                self._client = motor.motor_asyncio.AsyncIOMotorClient(mongodb_url, serverSelectionTimeoutMS=2000)
                self._db = self._client[db_name]
                logger.info(f"==> [MONGODB STATE REPOSITORY INITIALIZED] DB: '{db_name}'")
            except Exception as e:
                logger.warning(f"MongoDB client initialization failed: {e}. Active mode: InMemory fallback.")

    async def save_query_result(self, session_id: str, result: MarineQueryResult) -> None:
        await self._memory_fallback.save_query_result(session_id, result)
        if self._db is not None:
            try:
                doc = result.model_dump()
                doc["session_id"] = session_id
                doc["persisted"] = True
                await self._db.query_traces.insert_one(doc)
                result.persisted = True
                logger.info(f"==> [MONGODB SAVE SUCCESS] Session: '{session_id}' | Query: '{result.user_query}'")
            except Exception as e:
                logger.warning(f"MongoDB insert_one failed: {e}. Persisted in memory only.")

    async def get_query_history(self, session_id: str) -> list[MarineQueryResult]:
        if self._db is not None:
            try:
                cursor = self._db.query_traces.find({"session_id": session_id}).sort("timestamps.started_at", -1)
                docs = await asyncio.wait_for(cursor.to_list(length=100), timeout=1.5)
                if docs:
                    results = []
                    for d in docs:
                        d.pop("_id", None)
                        results.append(MarineQueryResult(**d))
                    return results
            except Exception as e:
                logger.warning(f"MongoDB query history fetch failed: {e}. Falling back to memory store.")
        
        # Memory store fallback
        return await self._memory_fallback.get_query_history(session_id)

    async def clear_history(self, session_id: str) -> None:
        await self._memory_fallback.clear_history(session_id)
        if self._db is not None:
            try:
                await self._db.query_traces.delete_many({"session_id": session_id})
            except Exception as e:
                logger.warning(f"MongoDB clear_history failed: {e}")

# Global state repository instance
state_repository = MongoStateRepository()

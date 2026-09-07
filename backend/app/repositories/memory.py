import asyncio
from typing import Optional
from app.repositories.interfaces import BaseStateRepository
from app.schemas.query import MarineQueryResult

class InMemoryStateRepository(BaseStateRepository):
    """
    Thread-safe, in-memory repository for temporary state management.
    Ensures zero external DB requirements for testing and Phase 1 runs.
    """
    
    def __init__(self):
        self._store: dict[str, list[MarineQueryResult]] = {}
        self._lock = asyncio.Lock()

    async def save_query_result(self, session_id: str, result: MarineQueryResult) -> None:
        async with self._lock:
            if session_id not in self._store:
                self._store[session_id] = []
            self._store[session_id].append(result)

    async def get_query_history(self, session_id: str) -> list[MarineQueryResult]:
        async with self._lock:
            return list(self._store.get(session_id, []))

    async def clear_history(self, session_id: str) -> None:
        async with self._lock:
            if session_id in self._store:
                del self._store[session_id]

# Singleton in-memory repository instance
state_repository = InMemoryStateRepository()

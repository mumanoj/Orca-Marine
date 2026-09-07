from abc import ABC, abstractmethod
from typing import Optional, Any
from app.schemas.query import MarineQueryResult

class BaseStateRepository(ABC):
    """
    Abstract Interface for state and trace persistence.
    Isolates agent execution from the underlying database vendor.
    """
    
    @abstractmethod
    async def save_query_result(self, session_id: str, result: MarineQueryResult) -> None:
        """
        Persist a MarineQueryResult linked to a session_id.
        """
        pass

    @abstractmethod
    async def get_query_history(self, session_id: str) -> list[MarineQueryResult]:
        """
        Retrieve query execution history for a session_id.
        """
        pass

    @abstractmethod
    async def clear_history(self, session_id: str) -> None:
        """
        Clear history for a given session.
        """
        pass

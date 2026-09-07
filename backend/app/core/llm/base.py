from abc import ABC, abstractmethod
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

class BaseLLMProvider(ABC):
    """
    Abstract base class for all LLM providers (e.g., Groq, Gemini).
    """
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the required credentials/configuration for the provider are available.
        """
        pass

    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> str:
        """
        Generate a text response for the given prompt.
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> T:
        """
        Generate a structured Pydantic object based on the response_model.
        """
        pass

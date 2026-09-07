import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from groq import AsyncGroq
from app.core.config import settings
from app.core.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)

class GroqProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.GROQ_API_KEY
        self.client = AsyncGroq(api_key=self.api_key) if self.api_key else None

    def is_available(self) -> bool:
        return self.api_key is not None and len(self.api_key.strip()) > 0

    async def generate_text(
        self, 
        prompt: str, 
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> str:
        if not self.is_available() or not self.client:
            raise ValueError("Groq API key is not configured or available.")

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})

        model = kwargs.pop("model", settings.GROQ_MODEL)
        
        response = await self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            **kwargs
        )
        return response.choices[0].message.content or ""

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> T:
        if not self.is_available() or not self.client:
            raise ValueError("Groq API key is not configured or available.")

        # Ensure LLM outputs JSON conforming to our schema
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_prompt = (
            f"{prompt}\n\nYou MUST respond ONLY with a raw JSON object that conforms strictly "
            f"to the following JSON Schema:\n{schema_json}"
        )

        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": augmented_prompt})

        model = kwargs.pop("model", settings.GROQ_MODEL)
        
        # Configure for JSON output mode
        response = await self.client.chat.completions.create(
            messages=messages,
            model=model,
            temperature=temperature,
            response_format={"type": "json_object"},
            **kwargs
        )
        
        content = response.choices[0].message.content or ""
        # Parse output into Pydantic model
        data = json.loads(content)
        return response_model.model_validate(data)

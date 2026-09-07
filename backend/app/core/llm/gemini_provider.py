import json
from typing import Type, TypeVar, Optional, Any
from pydantic import BaseModel
from google import genai
from google.genai import types
from app.core.config import settings
from app.core.llm.base import BaseLLMProvider

T = TypeVar("T", bound=BaseModel)

class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

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
            raise ValueError("Gemini API key is not configured or available.")

        model = kwargs.pop("model", settings.GEMINI_MODEL)
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction
        )
        
        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config=config
        )
        return response.text or ""

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> T:
        if not self.is_available() or not self.client:
            raise ValueError("Gemini API key is not configured or available.")

        model = kwargs.pop("model", settings.GEMINI_MODEL)
        schema_json = json.dumps(response_model.model_json_schema())
        augmented_prompt = (
            f"{prompt}\n\nYou MUST respond ONLY with a valid JSON object matching this schema:\n{schema_json}"
        )
        
        config = types.GenerateContentConfig(
            temperature=temperature,
            system_instruction=system_instruction,
            response_mime_type="application/json"
        )
        
        response = await self.client.aio.models.generate_content(
            model=model,
            contents=augmented_prompt,
            config=config
        )
        
        content = response.text or ""
        # Clean markdown codeblocks if LLM wraps in ```json
        content_clean = content.strip()
        if content_clean.startswith("```"):
            content_clean = content_clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        data = json.loads(content_clean)
        return response_model.model_validate(data)

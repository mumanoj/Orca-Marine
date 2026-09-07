import json
import logging
import re
from typing import Type, TypeVar, Optional, Any
import httpx
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class OllamaProvider(BaseLLMProvider):
    """
    Ollama Local LLM Provider for zero-cost, offline, rate-limit-free AI generation.
    Supports on-device models like qwen2.5, llama3.2, mistral, phi-3, functiongemma.
    """

    def __init__(self, host: Optional[str] = None, model: Optional[str] = None):
        self.host = host or getattr(settings, "OLLAMA_HOST", "http://127.0.0.1:11434")
        self.model = model or getattr(settings, "OLLAMA_MODEL", "qwen2.5:1.5b")
        self._is_alive: Optional[bool] = None

    def is_available(self) -> bool:
        """
        Quick check if Ollama server is running locally on self.host.
        """
        try:
            r = httpx.get(f"{self.host}/api/version", timeout=1.0)
            return r.status_code == 200
        except Exception:
            return False

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> str:
        """
        Generate text response locally via Ollama /api/generate endpoint.
        """
        target_model = kwargs.get("model") or self.model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system_instruction or "You are ORCA, an expert marine intelligence AI system.",
            "options": {"temperature": temperature},
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.host}/api/generate", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data.get("response", "").strip()

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        **kwargs: Any
    ) -> T:
        """
        Generate structured output conforming to response_model using Ollama JSON mode + structural repair.
        """
        schema_json = json.dumps(response_model.model_json_schema())
        system_prompt = (
            f"{system_instruction or 'You are ORCA, an expert marine intelligence assistant.'}\n\n"
            f"CRITICAL: You MUST respond ONLY with a valid JSON object strictly matching this Pydantic schema:\n"
            f"{schema_json}\n"
            f"Do NOT include markdown formatting or prose outside the JSON."
        )

        target_model = kwargs.get("model") or self.model
        payload = {
            "model": target_model,
            "prompt": prompt,
            "system": system_prompt,
            "format": "json",
            "options": {"temperature": temperature},
            "stream": False
        }
        headers = {"Content-Type": "application/json"}

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(f"{self.host}/api/generate", json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            raw_text = data.get("response", "").strip()

        # Structural & Regex Repair Layer (inspired by Kagami / FunctionGemma)
        cleaned_json = raw_text
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            cleaned_json = match.group(0)

        try:
            return response_model.model_validate_json(cleaned_json)
        except Exception as err:
            logger.warning(f"Ollama JSON parse error: {err}. Raw response: {raw_text}")
            raise err

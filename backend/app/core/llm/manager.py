import logging
import time
from typing import Type, TypeVar, Optional, Any, Dict
from pydantic import BaseModel

from app.core.config import settings
from app.core.llm.base import BaseLLMProvider
from app.core.llm.groq_provider import GroqProvider
from app.core.llm.gemini_provider import GeminiProvider
from app.core.llm.ollama_provider import OllamaProvider

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)

class CircuitBreaker:
    """
    Circuit breaker for skipping repeatedly failing LLM tiers temporarily.
    """
    def __init__(self, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.failure_counts: Dict[str, int] = {}
        self.circuit_open_until: Dict[str, float] = {}

    def is_open(self, tier_id: str) -> bool:
        now = time.time()
        open_until = self.circuit_open_until.get(tier_id, 0.0)
        if now < open_until:
            return True
        if open_until > 0.0 and now >= open_until:
            # Cooldown expired, reset circuit for trial
            self.circuit_open_until[tier_id] = 0.0
            self.failure_counts[tier_id] = 0
        return False

    def record_failure(self, tier_id: str, reason: str = ""):
        count = self.failure_counts.get(tier_id, 0) + 1
        self.failure_counts[tier_id] = count
        logger.warning(f"[CIRCUIT_BREAKER] Tier '{tier_id}' failure #{count}. Reason: {reason}")
        if count >= self.failure_threshold:
            self.circuit_open_until[tier_id] = time.time() + self.cooldown_seconds
            logger.error(f"[CIRCUIT_BREAKER] Circuit OPEN for Tier '{tier_id}' for {self.cooldown_seconds}s!")

    def record_success(self, tier_id: str):
        self.failure_counts[tier_id] = 0
        self.circuit_open_until[tier_id] = 0.0


class LLMManager:
    """
    Manager that wraps LLM providers in a strict 4-Tier Fallback Chain with Circuit Breakers & Validation Enforcement:
    
    TIER 1 (Primary):      Ollama local model with qwen2.5:7b-instruct
    TIER 2 (First backup): Ollama local model with qwen2.5:1.5b
    TIER 3 (Second backup): Gemini Cloud API (gemini-3.6-flash)
    TIER 4 (Final backup):  Groq Cloud API (groq/compound)
    """

    def __init__(self):
        self.ollama = OllamaProvider()
        self.groq = GroqProvider()
        self.gemini = GeminiProvider()
        self.circuit_breaker = CircuitBreaker(failure_threshold=3, cooldown_seconds=60.0)

    def get_provider_for_tier(self, tier_num: int) -> tuple[BaseLLMProvider, str, dict]:
        """
        Returns (provider_instance, tier_description, extra_kwargs).
        """
        if tier_num == 1:
            model_name = getattr(settings, "LLM_TIER_1_MODEL", "qwen2.5:7b-instruct")
            return self.ollama, f"Tier 1 (ollama:{model_name})", {"model": model_name}
        elif tier_num == 2:
            model_name = getattr(settings, "LLM_TIER_2_MODEL", "qwen2.5:1.5b")
            return self.ollama, f"Tier 2 (ollama:{model_name})", {"model": model_name}
        elif tier_num == 3:
            return self.gemini, "Tier 3 (gemini)", {}
        elif tier_num == 4:
            return self.groq, "Tier 4 (groq)", {}
        else:
            raise ValueError(f"Invalid tier number: {tier_num}")

    def get_active_tiers(self) -> list[int]:
        active = []
        if self.ollama.is_available():
            active.extend([1, 2])
        if self.gemini.is_available():
            active.append(3)
        if self.groq.is_available():
            active.append(4)
        return active

    def _get_tier_order(self, preferred_provider: Optional[str] = None) -> list[int]:
        """
        Build tier execution order according to user specs:
        1 -> 2 -> 3 -> 4
        Supports LLM_FORCE_TIER environment/config variable for testing!
        """
        force_tier = getattr(settings, "LLM_FORCE_TIER", None)
        if force_tier is not None:
            try:
                forced = int(force_tier)
                if 1 <= forced <= 4:
                    logger.info(f"[LLM_FORCE_TIER] Config forcing Tier {forced} execution.")
                    return [forced]
            except Exception:
                pass

        if preferred_provider is not None:
            pref = str(preferred_provider).lower()
            if "groq" in pref:
                return [4, 3, 1, 2]
            elif "gemini" in pref:
                return [3, 4, 1, 2]

        return [1, 2, 3, 4]

    async def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        preferred_provider: Optional[str] = None,
        **kwargs: Any
    ) -> tuple[str, str]:
        """
        Generate text through 4-Tier fallback chain with validation and circuit breaker.
        Returns tuple of (generated_text, tier_description).
        """
        tier_order = self._get_tier_order(preferred_provider)
        errors = []

        for tier_num in tier_order:
            tier_id = f"tier_{tier_num}"
            if self.circuit_breaker.is_open(tier_id):
                logger.warning(f"[LLM_TIER_AUDIT] Skipping Tier {tier_num} (Circuit Open)")
                errors.append(f"Tier {tier_num}: circuit breaker open")
                continue

            try:
                provider, tier_desc, extra_kwargs = self.get_provider_for_tier(tier_num)
                if not provider.is_available():
                    logger.debug(f"[LLM_TIER_AUDIT] Tier {tier_num} unavailable/unconfigured")
                    errors.append(f"Tier {tier_num}: unavailable")
                    continue

                call_kwargs = {**kwargs, **extra_kwargs}
                logger.info(f"[LLM_TIER_AUDIT] Attempting text generation with {tier_desc}")

                text = await provider.generate_text(
                    prompt,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    **call_kwargs
                )

                # Validation & Hallucination Check for Text Generation
                if not text or not text.strip():
                    raise ValueError(f"{tier_desc} returned empty or whitespace-only response.")

                self.circuit_breaker.record_success(tier_id)
                logger.info(f"[LLM_TIER_AUDIT] SUCCESS - Request handled by {tier_desc}")
                return text, tier_desc

            except Exception as e:
                error_msg = f"{tier_desc} failed: {str(e)}"
                logger.warning(f"[LLM_TIER_AUDIT] {error_msg}")
                self.circuit_breaker.record_failure(tier_id, reason=str(e))
                errors.append(error_msg)

        raise RuntimeError(f"All 4 LLM Tiers failed. Errors: {'; '.join(errors)}")

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_instruction: Optional[str] = None,
        temperature: float = 0.1,
        preferred_provider: Optional[str] = None,
        **kwargs: Any
    ) -> tuple[T, str]:
        """
        Generate Pydantic structured output through 4-Tier fallback chain with strict validation and circuit breaker.
        Returns tuple of (parsed_pydantic_object, tier_description).
        """
        tier_order = self._get_tier_order(preferred_provider)
        errors = []

        for tier_num in tier_order:
            tier_id = f"tier_{tier_num}"
            if self.circuit_breaker.is_open(tier_id):
                logger.warning(f"[LLM_TIER_AUDIT] Skipping Tier {tier_num} (Circuit Open)")
                errors.append(f"Tier {tier_num}: circuit breaker open")
                continue

            try:
                provider, tier_desc, extra_kwargs = self.get_provider_for_tier(tier_num)
                if not provider.is_available():
                    logger.debug(f"[LLM_TIER_AUDIT] Tier {tier_num} unavailable/unconfigured")
                    errors.append(f"Tier {tier_num}: unavailable")
                    continue

                call_kwargs = {**kwargs, **extra_kwargs}
                logger.info(f"[LLM_TIER_AUDIT] Attempting structured generation with {tier_desc}")

                obj = await provider.generate_structured(
                    prompt,
                    response_model,
                    system_instruction=system_instruction,
                    temperature=temperature,
                    **call_kwargs
                )

                # Validation & Hallucination Check for Structured Output
                if not isinstance(obj, response_model):
                    raise ValueError(f"{tier_desc} response model validation failed.")

                self.circuit_breaker.record_success(tier_id)
                logger.info(f"[LLM_TIER_AUDIT] SUCCESS - Request handled by {tier_desc}")
                return obj, tier_desc

            except Exception as e:
                error_msg = f"{tier_desc} failed: {str(e)}"
                logger.warning(f"[LLM_TIER_AUDIT] {error_msg}")
                self.circuit_breaker.record_failure(tier_id, reason=str(e))
                errors.append(error_msg)

        raise RuntimeError(f"All 4 LLM Tiers failed. Errors: {'; '.join(errors)}")

# Global single instance of LLMManager
llm_manager = LLMManager()

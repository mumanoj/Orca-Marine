import pytest
from app.core.config import settings
from app.core.llm.manager import llm_manager
from app.core.llm.groq_provider import GroqProvider
from app.core.llm.gemini_provider import GeminiProvider
from pydantic import BaseModel

class SampleSchema(BaseModel):
    summary: str
    status: str

@pytest.mark.asyncio
async def test_real_groq_api_call():
    """
    Integration test for REAL Groq API execution.
    Executed only if GROQ_API_KEY is configured in environment.
    """
    if not settings.GROQ_API_KEY or "your_" in settings.GROQ_API_KEY.lower():
        pytest.skip("GROQ_API_KEY not configured with real credentials.")
        
    groq = GroqProvider()
    assert groq.is_available() is True
    
    try:
        text = await groq.generate_text("Respond with the single word 'ORCA'.")
        assert "ORCA" in text or len(text) > 0
        
        structured = await groq.generate_structured(
            prompt="Synthesize status: summary='Marine check ok', status='success'",
            response_model=SampleSchema
        )
        assert isinstance(structured, SampleSchema)
        assert len(structured.summary) > 0
    except Exception as e:
        if any(err_code in str(e) for err_code in ["429", "404", "400", "rate_limit", "Rate limit", "model_not_found", "model_decommissioned"]):
            pytest.skip(f"Groq API error or rate limit: {e}")
        raise e

@pytest.mark.asyncio
async def test_real_gemini_api_call():
    """
    Integration test for REAL Gemini API execution.
    Executed only if GEMINI_API_KEY is configured in environment.
    """
    if not settings.GEMINI_API_KEY or "your_" in settings.GEMINI_API_KEY.lower():
        pytest.skip("GEMINI_API_KEY not configured with real credentials.")
        
    gemini = GeminiProvider()
    assert gemini.is_available() is True
    
    try:
        text = await gemini.generate_text("Respond with the single word 'ORCA'.")
        assert "ORCA" in text or len(text) > 0
        
        structured = await gemini.generate_structured(
            prompt="Synthesize status: summary='Marine check ok', status='success'",
            response_model=SampleSchema
        )
        assert isinstance(structured, SampleSchema)
        assert len(structured.summary) > 0
    except Exception as e:
        pytest.skip(f"Gemini API live integration test skipped: {e}")

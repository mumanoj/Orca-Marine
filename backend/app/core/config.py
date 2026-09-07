import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GROQ_API_KEY: Optional[str] = None
    GEMINI_API_KEY: Optional[str] = None
    GFW_API_KEY: Optional[str] = None
    
    MONGODB_URI: str = "mongodb://localhost:27017"
    MONGODB_DATABASE: str = "orca_db"

    @property
    def MONGODB_URL(self) -> str:
        return self.MONGODB_URI
    LLM_PRIMARY_PROVIDER: str = "ollama"
    LLM_SECONDARY_PROVIDER: str = "gemini"
    OLLAMA_HOST: str = "http://127.0.0.1:11434"
    LLM_TIER_1_MODEL: str = "qwen2.5:7b-instruct"
    LLM_TIER_2_MODEL: str = "qwen2.5:1.5b"
    LLM_FORCE_TIER: Optional[int] = None
    GROQ_MODEL: str = "groq/compound"
    GEMINI_MODEL: str = "gemini-3.6-flash"
    
    FIRST_LANGUAGE: str = "en"
    SECOND_LANGUAGE: str = "hi"
    
    WEATHER_API_BASE_URL: str = "https://api.open-meteo.com/v1/forecast"
    MARINE_API_BASE_URL: str = "https://marine-api.open-meteo.com/v1/marine"
    GEOCODING_API_BASE_URL: str = "https://nominatim.openstreetmap.org/search"
    
    SATELLITE_PROVIDER: str = "mock"
    SATELLITE_API_KEY: Optional[str] = None
    
    ALERT_API_BASE_URL: str = "https://api.weather.gov/alerts"
    ROUTING_API_BASE_URL: str = "http://router.project-osrm.org/route/v1"
    
    JWT_SECRET: str = "supersecretjwtkeyfororcaplatformphase1dev"
    JWT_REFRESH_SECRET: str = "supersecretjwtrefreshkeyfororcaplatformphase1dev"
    
    ADMIN_EMAIL: str = "admin@orca.marine"
    ADMIN_PASSWORD: str = "adminpasswordchangeinprod"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()

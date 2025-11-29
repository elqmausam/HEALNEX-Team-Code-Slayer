# hospital_agent/core/config.py
"""
Configuration management with environment variables
"""

from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    APP_NAME: str = "Hospital Agent"
    DEBUG: bool = False
    API_VERSION: str = "v1"
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # Options: "openai", "gemini", "llama"
    
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4.1"
    
    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"  # or "gemini-1.5-pro"
    
    # Llama
    LLAMA_MODEL_PATH: Optional[str] = None
    LLAMA_API_URL: Optional[str] = None
    
    # Model Parameters
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2048
    LLM_TIMEOUT: int = 60
    
    # Vector Database (Pinecone)
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_ENVIRONMENT: str = "us-east-1"
    PINECONE_INDEX_NAME: str = "hospital-protocols"
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSION: int = 1536
    

    # Redis Cache
    REDIS_URL: str = "redis://hospital-redis:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    CACHE_TTL: int = 3600  # 1 hour
    CACHE_MAX_CONNECTIONS: int = 50
    
    # Database (PostgreSQL for metadata)
    DATABASE_URL: str = "postgresql://user:password@localhost:5432/hospital_agent"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10
    
    # External APIs (Free, No Keys Required)
    WEATHER_API_URL: str = "https://api.open-meteo.com/v1/forecast"
    AQI_API_URL: str = "https://air-quality-api.open-meteo.com/v1/air-quality"
    
    # HMIS Integration
    HMIS_API_URL: Optional[str] = None
    HMIS_API_KEY: Optional[str] = None
    
    # Lab System Integration
    LAB_API_URL: Optional[str] = None
    LAB_API_KEY: Optional[str] = None
    
    # Voice Processing
    WHISPER_MODEL: str = "whisper-1"
    TTS_MODEL: str = "tts-1"
    TTS_VOICE: str = "alloy"
    
    # Performance Settings
    REQUEST_TIMEOUT: int = 30
    MAX_CONCURRENT_REQUESTS: int = 100
    BATCH_SIZE: int = 32
    
    # Memory Settings
    MAX_CONVERSATION_HISTORY: int = 50
    MEMORY_RETENTION_DAYS: int = 90
    
    # Monitoring
    ENABLE_METRICS: bool = True
    METRICS_PORT: int = 9090
    LOG_LEVEL: str = "INFO"
    
    # Security
    JWT_SECRET_KEY: str = "change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24
    
    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()


# hospital_agent/core/__init__.py
from .config import settings, get_settings

__all__ = ["settings", "get_settings"]
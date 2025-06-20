# app/config.py - Working Configuration File

from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import Optional, List

class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"  # This allows extra fields in .env without validation errors
    )
    
    # Database settings
    DATABASE_URL: str = "sqlite:///./chatbot.db"
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_DB: Optional[str] = None
    
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: Optional[str] = "localhost"
    REDIS_PORT: Optional[str] = "6379"
    
    # OpenAI settings
    OPENAI_API_KEY: str = "your-openai-api-key-here"
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: Optional[str] = "0.7"
    OPENAI_MAX_TOKENS: Optional[str] = "1000"
    EMBEDDINGS_MODEL: Optional[str] = "text-embedding-ada-002"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: Optional[str] = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    
    # App settings
    APP_NAME: str = "AI Chatbot API"
    DEBUG: bool = True
    VERSION: str = "1.0.0"
    ENVIRONMENT: Optional[str] = "development"
    
    # CORS settings
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    CORS_ORIGINS: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_FOLDER: str = "uploads"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # Parse CORS_ORIGINS if provided
        if self.CORS_ORIGINS:
            origins = [origin.strip() for origin in self.CORS_ORIGINS.split(',')]
            self.ALLOWED_ORIGINS = origins

# Create settings instance with error handling
try:
    settings = Settings()
    print("✅ Settings loaded successfully")
except Exception as e:
    print(f"❌ Settings loading failed: {e}")
    # Create fallback settings
    class FallbackSettings:
        APP_NAME = "AI Chatbot API"
        VERSION = "1.0.0"
        DEBUG = True
        ALLOWED_ORIGINS = ["*"]
        DATABASE_URL = "sqlite:///./chatbot.db"
        SECRET_KEY = "fallback-secret-key"
        OPENAI_API_KEY = "not-set"
    
    settings = FallbackSettings()
    print("⚠️  Using fallback settings")
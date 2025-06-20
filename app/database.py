from pydantic import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database settings
    DATABASE_URL: str = "postgresql://username:password@localhost:5432/chatbot_db"
    REDIS_URL: str = "redis://localhost:6379"
    
    # OpenAI settings
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # JWT settings
    SECRET_KEY: str = "your-secret-key-change-this"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
    
    # App settings
    APP_NAME: str = "AI Chatbot API"
    DEBUG: bool = False
    VERSION: str = "1.0.0"
    
    # CORS settings
    ALLOWED_ORIGINS: list = ["*"]
    
    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # File upload settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    UPLOAD_FOLDER: str = "uploads"
    
    class Config:
        env_file = ".env"

settings = Settings()
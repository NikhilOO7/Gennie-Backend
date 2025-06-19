"""Application configuration with proper Pydantic settings."""

import os
from typing import Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with validation."""
    
    # Database
    DATABASE_URL: str = ""
    POSTGRES_USER: str = "chatbot_user"
    POSTGRES_PASSWORD: str = "chatbot_password"
    POSTGRES_DB: str = "chatbot_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_HOST: str = "localhost"
    REDIS_PORT: str = "6379"
    
    # OpenAI
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 1000
    EMBEDDINGS_MODEL: str = "text-embedding-ada-002"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,*"
    
    # Application
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env

# Create settings instance
settings = Settings()

# Validate required settings
if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

if settings.ENVIRONMENT == "production" and settings.SECRET_KEY == "your-secret-key-here":
    raise ValueError("SECRET_KEY must be set for production environment")
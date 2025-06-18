import os
from typing import Optional, List
from pydantic_settings import BaseSettings
import json

class Settings(BaseSettings):
    # Database Configuration
    database_url: str = os.getenv("DATABASE_URL", 
        "postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # OpenAI Configuration
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    openai_temperature: float = float(os.getenv("OPENAI_TEMPERATURE", "0.7"))
    openai_max_tokens: int = int(os.getenv("OPENAI_MAX_TOKENS", "1000"))
    
    # Embeddings (if you need it later)
    embeddings_model: str = os.getenv("EMBEDDINGS_MODEL", "text-embedding-ada-002")
    
    # Security Configuration
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Application Configuration
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"
    host: str = os.getenv("HOST", "0.0.0.0")
    port: int = int(os.getenv("PORT", "8000"))
    
    # API Configuration
    api_v1_str: str = "/api/v1"
    project_name: str = "AI Chatbot Backend"
    project_version: str = "1.0.0"
    
    # CORS Configuration - handle the JSON string from .env
    cors_origins: List[str] = []
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Parse CORS origins from environment variable
        cors_env = os.getenv("CORS_ORIGINS", '["*"]')
        try:
            if cors_env.startswith('[') and cors_env.endswith(']'):
                # It's a JSON array string
                self.cors_origins = json.loads(cors_env)
            else:
                # It's a simple string, split by comma
                self.cors_origins = [origin.strip() for origin in cors_env.split(',')]
        except (json.JSONDecodeError, ValueError):
            # Fallback to default
            self.cors_origins = ["*"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "allow"  # Allow extra fields from .env

# Create global settings instance
settings = Settings()
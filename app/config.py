from pydantic_settings import BaseSettings
from pydantic import Field, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    """
    Application settings using Pydantic Settings (modern approach)
    """
    # Application Configuration
    APP_NAME: str = Field(default="AI Chatbot Backend", description="Application name")
    VERSION: str = Field(default="1.0.0", description="Application version")
    ENVIRONMENT: str = Field(default="development", description="Environment (development/production)")
    DEBUG: bool = Field(default=True, description="Debug mode")
    
    # Database Configuration
    DATABASE_URL: str = Field(..., description="PostgreSQL database URL")
    POSTGRES_USER: str = Field(..., description="PostgreSQL username")
    POSTGRES_PASSWORD: str = Field(..., description="PostgreSQL password")
    POSTGRES_DB: str = Field(..., description="PostgreSQL database name")
    
    # Redis Configuration
    REDIS_URL: str = Field(..., description="Redis connection URL")
    REDIS_HOST: str = Field(default="localhost", description="Redis host")
    REDIS_PORT: int = Field(default=6379, description="Redis port")
    
    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(..., description="OpenAI API key")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", description="Default OpenAI model")
    OPENAI_TEMPERATURE: float = Field(default=0.7, ge=0.0, le=2.0, description="OpenAI temperature")
    OPENAI_MAX_TOKENS: int = Field(default=1000, ge=1, le=4000, description="Max tokens for OpenAI")
    EMBEDDINGS_MODEL: str = Field(default="text-embedding-ada-002", description="Embeddings model")
    
    # Security Configuration
    SECRET_KEY: str = Field(..., min_length=32, description="Secret key for JWT tokens")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm (deprecated, use JWT_ALGORITHM)")
    JWT_ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, ge=1, description="Token expiration in minutes")
    
    # CORS Configuration
    CORS_ORIGINS: str = Field(
        default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000",
        description="Allowed CORS origins (comma-separated)"
    )
    
    # Computed properties
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        """Parse CORS origins from string to list"""
        if self.CORS_ORIGINS == "*":
            return ["*"]
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]
    
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment value"""
        allowed = ["development", "staging", "production"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @validator("DEBUG")
    def set_debug_from_environment(cls, v, values):
        """Set debug mode based on environment"""
        env = values.get("ENVIRONMENT", "development")
        if env == "production":
            return False
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v.startswith(("postgresql://", "postgresql+psycopg2://")):
            raise ValueError("DATABASE_URL must start with postgresql:// or postgresql+psycopg2://")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v
    
    @validator("OPENAI_API_KEY")
    def validate_openai_key(cls, v):
        """Validate OpenAI API key format"""
        if not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with sk-")
        return v
    
    # Additional computed properties for convenience
    @property
    def IS_DEVELOPMENT(self) -> bool:
        return self.ENVIRONMENT == "development"
    
    @property
    def IS_PRODUCTION(self) -> bool:
        return self.ENVIRONMENT == "production"
    
    @property
    def DATABASE_CONFIG(self) -> dict:
        """Get database configuration dictionary"""
        return {
            "url": self.DATABASE_URL,
            "user": self.POSTGRES_USER,
            "password": self.POSTGRES_PASSWORD,
            "database": self.POSTGRES_DB,
            "echo": self.DEBUG
        }
    
    @property
    def REDIS_CONFIG(self) -> dict:
        """Get Redis configuration dictionary"""
        return {
            "url": self.REDIS_URL,
            "host": self.REDIS_HOST,
            "port": self.REDIS_PORT,
            "decode_responses": True
        }
    
    @property
    def OPENAI_CONFIG(self) -> dict:
        """Get OpenAI configuration dictionary"""
        return {
            "api_key": self.OPENAI_API_KEY,
            "model": self.OPENAI_MODEL,
            "temperature": self.OPENAI_TEMPERATURE,
            "max_tokens": self.OPENAI_MAX_TOKENS,
            "embeddings_model": self.EMBEDDINGS_MODEL
        }
    
    @property
    def JWT_CONFIG(self) -> dict:
        """Get JWT configuration dictionary"""
        return {
            "secret_key": self.SECRET_KEY,
            "algorithm": self.JWT_ALGORITHM,
            "expire_minutes": self.ACCESS_TOKEN_EXPIRE_MINUTES
        }

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        validate_assignment = True

# Create global settings instance
settings = Settings()

# Logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s",
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "logging.FileHandler",
            "filename": "app.log",
            "mode": "a",
        },
    },
    "root": {
        "level": "DEBUG" if settings.DEBUG else "INFO",
        "handlers": ["default", "file"],
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["default"],
            "propagate": False,
        },
        "sqlalchemy.engine": {
            "level": "INFO" if settings.DEBUG else "WARNING",
            "handlers": ["default"],
            "propagate": False,
        },
    },
}
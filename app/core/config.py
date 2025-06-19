"""
Application configuration settings
"""

import os
from typing import List, Union, Any
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings from environment variables"""
    
    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Database settings
    database_url: str = Field(
        default="postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db",
        description="Database connection URL"
    )
    
    # Redis settings  
    redis_url: str = Field(
        default="redis://localhost:6379",
        description="Redis connection URL"
    )
    
    # OpenAI settings
    openai_api_key: str = Field(
        default="your_openai_api_key_here",
        description="OpenAI API key"
    )
    openai_model: str = Field(
        default="gpt-3.5-turbo",
        description="OpenAI model to use"
    )
    openai_temperature: float = Field(
        default=0.7,
        description="OpenAI temperature setting"
    )
    openai_max_tokens: int = Field(
        default=1000,
        description="Maximum tokens for OpenAI responses"
    )
    
    # Embeddings model
    embeddings_model: str = Field(
        default="text-embedding-ada-002",
        description="Embeddings model to use"
    )
    
    # Application settings
    secret_key: str = Field(
        default="your-super-secret-key-change-this-in-production-min-32-chars-long",
        description="Secret key for JWT tokens"
    )
    debug: bool = Field(
        default=True,
        description="Debug mode"
    )
    environment: str = Field(
        default="development",
        description="Application environment"
    )
    
    # JWT settings
    jwt_algorithm: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="JWT token expiration in minutes"
    )
    
    # CORS settings - handle both string and list formats
    cors_origins: Union[str, List[str]] = Field(
        default="http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,*",
        description="CORS allowed origins"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse CORS origins from string or list format"""
        if isinstance(v, str):
            # Handle comma-separated string
            if v.startswith('[') and v.endswith(']'):
                # Handle JSON-like string format
                import json
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    # Fallback to comma-separated parsing
                    return [origin.strip().strip('"\'') for origin in v.strip('[]').split(',')]
            else:
                # Handle simple comma-separated string
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        elif isinstance(v, list):
            return v
        else:
            return ["*"]  # Default fallback
    
    # API settings
    api_v1_str: str = Field(
        default="/api/v1",
        description="API version 1 prefix"
    )
    
    # Project settings
    project_name: str = Field(
        default="Chat Backend API",
        description="Project name"
    )
    project_version: str = Field(
        default="1.0.0",
        description="Project version"
    )


# Create settings instance
settings = Settings()
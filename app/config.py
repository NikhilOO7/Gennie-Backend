"""
Configuration Management for AI Chatbot Backend
Pydantic Settings and comprehensive validation
"""

from pydantic import BaseModel, validator, SecretStr, AnyHttpUrl
from typing import List, Optional, Union
import os
from dotenv import load_dotenv
from functools import lru_cache

# Load .env file explicitly
load_dotenv()

class Settings(BaseModel):
    """
    Application settings with comprehensive validation and defaults
    """
    
    # Application Settings
    APP_NAME: str = "AI Chatbot Backend"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    
    # Server Settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    WORKERS: int = 1
    
    # Security Settings
    SECRET_KEY: SecretStr = SecretStr(os.getenv("SECRET_KEY", "your-super-secret-key-change-in-production"))
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PASSWORD_MIN_LENGTH: int = 8
    ALLOWED_HOSTS: List[str] = ["*"]
    
    # CORS Settings
    FRONTEND_URL: Optional[AnyHttpUrl] = None
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8080"]
    
    # Database Settings
    DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/chatbot_db"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600
    
    # Redis Settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_PASSWORD: Optional[str] = None
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 10
    REDIS_RETRY_ON_TIMEOUT: bool = True
    REDIS_SOCKET_TIMEOUT: int = 5
    REDIS_CONNECTION_TIMEOUT: int = 5
    
    # Google Cloud Configuration (Gemini)
    GOOGLE_CLOUD_PROJECT_ID: str = os.getenv("GOOGLE_CLOUD_PROJECT_ID", "")
    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./credentials.json")
    GOOGLE_CLOUD_LOCATION: str = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    GEMINI_API_KEY: Optional[SecretStr] = SecretStr(os.getenv("GEMINI_API_KEY", "")) if os.getenv("GEMINI_API_KEY") else None
    
    # OpenAI Settings (kept for backward compatibility and configuration reuse)
    OPENAI_API_KEY: SecretStr = SecretStr(os.getenv("OPENAI_API_KEY", "your-openai-api-key"))
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    OPENAI_TEMPERATURE: float = 0.7
    OPENAI_MAX_TOKENS: int = 1000
    OPENAI_TOP_P: float = 1.0
    OPENAI_FREQUENCY_PENALTY: float = 0.0
    OPENAI_PRESENCE_PENALTY: float = 0.0
    OPENAI_TIMEOUT: int = 30
    OPENAI_MAX_RETRIES: int = 3
    
    # Audio Settings
    MAX_AUDIO_SIZE_MB: int = 10
    SUPPORTED_AUDIO_FORMATS: List[str] = ["wav", "mp3", "webm", "ogg", "m4a"]
    AUDIO_SAMPLE_RATE: int = 16000
    
    # Embeddings Settings
    EMBEDDINGS_MODEL: str = "text-embedding-ada-002"
    EMBEDDINGS_DIMENSION: int = 1536
    
    # Conversation Settings
    MAX_CONVERSATION_LENGTH: int = 50
    MAX_MESSAGE_LENGTH: int = 4000
    CONVERSATION_CONTEXT_WINDOW: int = 10
    DEFAULT_SYSTEM_PROMPT: str = "You are a helpful AI assistant."
    
    # Rate Limiting Settings
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60
    RATE_LIMIT_STORAGE: str = "redis"
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10485760  # 10MB
    ALLOWED_FILE_TYPES: List[str] = [".txt", ".pdf", ".docx", ".md"]
    UPLOAD_DIR: str = "uploads"
    
    # Monitoring Settings
    ENABLE_METRICS: bool = True
    METRICS_ENDPOINT: str = "/metrics"
    HEALTH_CHECK_INTERVAL: int = 30
    
    # WebSocket Settings
    WEBSOCKET_TIMEOUT: int = 600
    WEBSOCKET_MAX_SIZE: int = 1048576
    WEBSOCKET_PING_INTERVAL: int = 30
    WEBSOCKET_PING_TIMEOUT: int = 10
    
    # Emotion Analysis Settings
    EMOTION_ANALYSIS_ENABLED: bool = True
    EMOTION_CONFIDENCE_THRESHOLD: float = 0.6
    EMOTION_MODELS: List[str] = ["vader", "textblob"]
    
    # Personalization Settings
    PERSONALIZATION_ENABLED: bool = True
    PERSONALIZATION_CACHE_TTL: int = 3600
    MIN_INTERACTIONS_FOR_PERSONALIZATION: int = 5
    
    # Background Tasks Settings
    ENABLE_BACKGROUND_TASKS: bool = True
    TASK_QUEUE_NAME: str = "chatbot_tasks"
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    
    # Caching Settings
    CACHE_ENABLED: bool = True
    CACHE_DEFAULT_TTL: int = 300
    CACHE_MAX_SIZE: int = 1000
    
    # Email Settings (Optional)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[SecretStr] = None
    SMTP_USE_TLS: bool = True
    FROM_EMAIL: Optional[str] = None
    
    # Testing Settings
    TESTING: bool = False
    TEST_DATABASE_URL: Optional[str] = None
    TEST_REDIS_URL: Optional[str] = None
    
    # Logging Settings
    LOG_JSON_FORMAT: bool = False
    LOG_FILE_ENABLED: bool = True
    LOG_FILE_PATH: str = "logs/app.log"
    LOG_FILE_MAX_SIZE: int = 10485760  # 10MB
    LOG_FILE_BACKUP_COUNT: int = 5
    
    # Advanced Settings
    WORKER_CLASS: str = "uvicorn.workers.UvicornWorker"
    RATE_LIMIT_PER_MINUTE: int = 60
    CONNECTION_POOL_MAX_SIZE: int = 100
    REQUEST_TIMEOUT: int = 60
    SLOW_REQUEST_THRESHOLD: float = 5.0
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = True
        use_enum_values = True
    
    # Validators
    @validator("ENVIRONMENT")
    def validate_environment(cls, v):
        """Validate environment setting"""
        allowed_envs = ["development", "staging", "production", "testing"]
        if v not in allowed_envs:
            raise ValueError(f"Environment must be one of: {allowed_envs}")
        return v
    
    @validator("LOG_LEVEL")
    def validate_log_level(cls, v):
        """Validate log level"""
        allowed_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in allowed_levels:
            raise ValueError(f"Log level must be one of: {allowed_levels}")
        return v.upper()
    
    @validator("SECRET_KEY")
    def validate_secret_key(cls, v):
        """Validate secret key strength"""
        secret = v.get_secret_value() if hasattr(v, 'get_secret_value') else v
        if len(secret) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v
    
    @validator("DATABASE_URL")
    def validate_database_url(cls, v):
        """Validate database URL format"""
        if not v.startswith(("postgresql://", "postgresql+asyncpg://", "sqlite:///")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL or SQLite URL")
        return v
    
    @validator("REDIS_URL")
    def validate_redis_url(cls, v):
        """Validate Redis URL format"""
        if not v.startswith("redis://"):
            raise ValueError("REDIS_URL must start with redis://")
        return v
    
    @validator("GOOGLE_CLOUD_PROJECT_ID")
    def validate_gcp_project(cls, v):
        """Validate Google Cloud Project ID"""
        if v and not v.strip():
            raise ValueError("GOOGLE_CLOUD_PROJECT_ID cannot be empty if provided")
        return v
    
    @validator("GOOGLE_CLOUD_LOCATION")
    def validate_gcp_location(cls, v):
        """Validate Google Cloud Location"""
        valid_locations = ["us-central1", "us-east1", "us-west1", "europe-west1", "europe-west4", "asia-northeast1"]
        if v and v not in valid_locations:
            logger.warning(f"Unusual GCP location: {v}. Common locations are: {valid_locations}")
        return v
    
    @validator("OPENAI_TEMPERATURE")
    def validate_temperature(cls, v):
        """Validate OpenAI temperature range"""
        if not 0.0 <= v <= 2.0:
            raise ValueError("OPENAI_TEMPERATURE must be between 0.0 and 2.0")
        return v
    
    @validator("OPENAI_TOP_P")
    def validate_top_p(cls, v):
        """Validate OpenAI top_p range"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("OPENAI_TOP_P must be between 0.0 and 1.0")
        return v
    
    @validator("OPENAI_FREQUENCY_PENALTY", "OPENAI_PRESENCE_PENALTY")
    def validate_penalties(cls, v):
        """Validate OpenAI penalty range"""
        if not -2.0 <= v <= 2.0:
            raise ValueError("OpenAI penalties must be between -2.0 and 2.0")
        return v
    
    @validator("MAX_FILE_SIZE")
    def validate_file_size(cls, v):
        """Validate max file size (in bytes)"""
        if v <= 0:
            raise ValueError("MAX_FILE_SIZE must be positive")
        if v > 100 * 1024 * 1024:  # 100MB
            raise ValueError("MAX_FILE_SIZE cannot exceed 100MB")
        return v
    
    @validator("CORS_ORIGINS", pre=True)
    def validate_cors_origins(cls, v):
        """Validate CORS origins"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @validator("ALLOWED_HOSTS", pre=True)
    def validate_allowed_hosts(cls, v):
        """Validate allowed hosts"""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @property
    def is_development(self) -> bool:
        """Check if running in development mode"""
        return self.ENVIRONMENT == "development"
    
    @property
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return self.ENVIRONMENT == "production"
    
    @property
    def is_testing(self) -> bool:
        """Check if running in testing mode"""
        return self.ENVIRONMENT == "testing" or self.TESTING
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic"""
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    @property
    def effective_database_url(self) -> str:
        """Get effective database URL (test DB if testing)"""
        if self.is_testing and self.TEST_DATABASE_URL:
            return self.TEST_DATABASE_URL
        return self.DATABASE_URL
    
    def get_openai_api_key(self) -> str:
        """Get OpenAI API key as string"""
        return self.OPENAI_API_KEY.get_secret_value()
    
    def get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key as string"""
        if self.GEMINI_API_KEY:
            return self.GEMINI_API_KEY.get_secret_value()
        return None
    
    def get_secret_key(self) -> str:
        """Get secret key as string"""
        return self.SECRET_KEY.get_secret_value()
    
    def get_smtp_password(self) -> Optional[str]:
        """Get SMTP password as string"""
        if self.SMTP_PASSWORD:
            return self.SMTP_PASSWORD.get_secret_value()
        return None

# Environment-specific settings classes
class DevelopmentSettings(Settings):
    """Development environment settings"""
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "DEBUG"
    DATABASE_ECHO: bool = True
    RELOAD: bool = True
    RATE_LIMIT_ENABLED: bool = False
    LOG_JSON_FORMAT: bool = False  # Disable JSON logging in development
    LOG_FILE_ENABLED: bool = False  # Disable file logging in development
    RATE_LIMIT_PER_MINUTE: int = 1000  # Higher rate limit for development

class ProductionSettings(Settings):
    """Production environment settings"""
    ENVIRONMENT: str = "production"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    DATABASE_ECHO: bool = False
    RELOAD: bool = False
    ALLOWED_HOSTS: List[str] = []  # Must be set in production
    RATE_LIMIT_ENABLED: bool = True

class TestingSettings(Settings):
    """Testing environment settings"""
    ENVIRONMENT: str = "testing"
    TESTING: bool = True
    LOG_LEVEL: str = "WARNING"
    DATABASE_ECHO: bool = False
    RATE_LIMIT_ENABLED: bool = False
    PERSONALIZATION_ENABLED: bool = False

@lru_cache()
def get_settings() -> Settings:
    """
    Get settings instance with caching
    Factory function that returns appropriate settings based on environment
    """
    env = os.getenv("ENVIRONMENT", "development").lower()
    
    if env == "production":
        return ProductionSettings()
    elif env == "testing":
        return TestingSettings()
    else:
        return DevelopmentSettings()

# Global settings instance
settings = get_settings()

# Export commonly used settings
__all__ = [
    "Settings",
    "DevelopmentSettings", 
    "ProductionSettings",
    "TestingSettings",
    "get_settings",
    "settings"
]
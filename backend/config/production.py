import os
from typing import List
from app.config import Settings

class ProductionSettings(Settings):
    """Production-specific configuration"""
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY")  # Must be set in production
    ALLOWED_HOSTS: List[str] = ["yourdomain.com", "api.yourdomain.com"]
    CORS_ORIGINS: List[str] = ["https://yourdomain.com"]
    
    # SSL/TLS
    SSL_REDIRECT: bool = True
    SECURE_COOKIES: bool = True
    SESSION_COOKIE_SECURE: bool = True
    CSRF_COOKIE_SECURE: bool = True
    
    # Database
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 30
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis
    REDIS_MAX_CONNECTIONS: int = 100
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_JSON_FORMAT: bool = True
    LOG_FILE_ENABLED: bool = True
    
    # Monitoring
    HEALTH_CHECK_TIMEOUT: int = 5
    METRICS_ENABLED: bool = True
    
    class Config:
        env_file = ".env.production"
        case_sensitive = True
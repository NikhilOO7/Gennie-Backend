from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import redis.asyncio as redis
from app.core.config import settings

# SQLAlchemy Database Engine
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=settings.debug  # Log SQL queries in debug mode
)

# Session factory
SessionLocal = sessionmaker(
    autocommit=False, 
    autoflush=False, 
    bind=engine
)

# Base class for models
Base = declarative_base()

# Redis connection
redis_client = redis.from_url(
    settings.redis_url, 
    encoding="utf-8", 
    decode_responses=True,
    max_connections=20
)

# Database dependency for FastAPI
def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Redis dependency for FastAPI
async def get_redis():
    """Dependency to get Redis client"""
    return redis_client

# Database connection test
def test_database_connection():
    """Test database connectivity"""
    try:
        with engine.connect() as connection:
            connection.execute("SELECT 1")
        return True
    except Exception as e:
        print(f"Database connection failed: {e}")
        return False

# Redis connection test
async def test_redis_connection():
    """Test Redis connectivity"""
    try:
        await redis_client.ping()
        return True
    except Exception as e:
        print(f"Redis connection failed: {e}")
        return False
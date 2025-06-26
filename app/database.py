from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
import redis.asyncio as redis
import logging
import os
from typing import Generator

from app.config import settings

logger = logging.getLogger(__name__)

# Database setup
try:
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=10,
        max_overflow=20,
        echo=settings.DEBUG
    )
    
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base = declarative_base()
    
    logger.info("✅ Database engine created successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to create database engine: {str(e)}")
    # Don't raise here, let the app start but log the error
    engine = None
    SessionLocal = None
    Base = None

# Redis setup
try:
    redis_client = redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5,
        retry_on_timeout=True,
        health_check_interval=30
    )
    logger.info("✅ Redis client created successfully")
    
except Exception as e:
    logger.error(f"❌ Failed to create Redis client: {str(e)}")
    redis_client = None

def get_db() -> Generator[Session, None, None]:
    """
    Database session dependency with proper error handling
    """
    if not SessionLocal:
        logger.error("⚠️ Database module not available - SessionLocal is None")
        raise Exception("Database module not available")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def get_redis():
    """
    Redis client dependency with proper error handling
    """
    if not redis_client:
        logger.error("⚠️ Redis module not available - redis_client is None")
        raise Exception("Redis module not available")
    
    try:
        # Test connection
        await redis_client.ping()
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection error: {str(e)}")
        raise Exception("Redis connection failed")

def check_db_health() -> bool:
    """
    Check database connection health
    """
    if not engine:
        logger.warning("⚠️ Database module not available")
        return False
    
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("✅ Database health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        return False

async def check_redis_health() -> bool:
    """
    Check Redis connection health
    """
    if not redis_client:
        logger.warning("⚠️ Redis module not available")
        return False
    
    try:
        await redis_client.ping()
        logger.info("✅ Redis health check passed")
        return True
    except Exception as e:
        logger.error(f"❌ Redis health check failed: {str(e)}")
        return False

async def create_tables():
    """
    Create database tables if they don't exist
    """
    if not engine or not Base:
        logger.error("⚠️ Database module not available - cannot create tables")
        return False
    
    try:
        # Import all models to ensure they're registered with Base
        from app.models.user import User
        from app.models.chat import Chat  
        from app.models.message import Message
        from app.models.emotion import Emotion
        from app.models.user_preferences import UserPreferences
        
        logger.info("✅ All models imported successfully")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables created/verified successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to create database tables: {str(e)}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return False

@contextmanager
def get_db_context():
    """
    Context manager for database sessions
    """
    if not SessionLocal:
        raise Exception("Database module not available")
    
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database context error: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

async def init_redis_connection():
    """
    Initialize Redis connection with retry logic
    """
    global redis_client
    
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            if redis_client:
                await redis_client.ping()
                logger.info("✅ Redis connection initialized successfully")
                return True
            else:
                redis_client = redis.from_url(
                    settings.REDIS_URL,
                    encoding="utf-8",
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True,
                    health_check_interval=30
                )
                await redis_client.ping()
                logger.info("✅ Redis connection re-established")
                return True
                
        except Exception as e:
            retry_count += 1
            logger.warning(f"⚠️ Redis connection attempt {retry_count} failed: {str(e)}")
            if retry_count >= max_retries:
                logger.error("❌ Failed to initialize Redis connection after all retries")
                return False
    
    return False

async def close_connections():
    """
    Close all database and Redis connections
    """
    try:
        if redis_client:
            await redis_client.close()
            logger.info("✅ Redis connection closed")
        
        if engine:
            engine.dispose()
            logger.info("✅ Database engine disposed")
            
    except Exception as e:
        logger.error(f"❌ Error closing connections: {str(e)}")

# Health check functions for the application
def get_database_info():
    """
    Get database connection information
    """
    if not engine:
        return {"status": "unavailable", "url": "not configured"}
    
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            return {
                "status": "connected",
                "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "hidden",
                "version": version,
                "pool_size": engine.pool.size(),
                "checked_out": engine.pool.checkedout()
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": settings.DATABASE_URL.split("@")[1] if "@" in settings.DATABASE_URL else "hidden"
        }

async def get_redis_info():
    """
    Get Redis connection information
    """
    if not redis_client:
        return {"status": "unavailable", "url": "not configured"}
    
    try:
        info = await redis_client.info()
        return {
            "status": "connected",
            "url": settings.REDIS_URL.split("@")[1] if "@" in settings.REDIS_URL else settings.REDIS_URL,
            "version": info.get("redis_version", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory_human", "unknown")
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "url": settings.REDIS_URL.split("@")[1] if "@" in settings.REDIS_URL else settings.REDIS_URL
        }
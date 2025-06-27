"""
Database Configuration and Connection Management
with async SQLAlchemy 2.0+ and comprehensive connection handling
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text, event
from sqlalchemy.pool import StaticPool
from contextlib import asynccontextmanager
import logging
import asyncio
from typing import AsyncGenerator, Optional
import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError

from app.config import settings

logger = logging.getLogger(__name__)

# Database URL configuration
if settings.is_testing:
    # Use in-memory SQLite for testing
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    SYNC_DATABASE_URL = "sqlite:///:memory:"
else:
    # Convert to async URL for production/development
    DATABASE_URL = settings.effective_database_url
    if "postgresql://" in DATABASE_URL:
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
    SYNC_DATABASE_URL = settings.database_url_sync

# Create async engine with optimized settings
engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    # SQLite specific settings
    poolclass=StaticPool if "sqlite" in DATABASE_URL else None,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    # Connection pool settings
    pool_pre_ping=True,  # Verify connections before use
    pool_reset_on_return='commit',  # Reset connections on return
)

# Create sync engine for Alembic migrations
sync_engine = create_engine(
    SYNC_DATABASE_URL,
    echo=settings.DATABASE_ECHO,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    poolclass=StaticPool if "sqlite" in SYNC_DATABASE_URL else None,
    connect_args={"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {},
    pool_pre_ping=True,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Create base class for models
Base = declarative_base()

# Redis connection
redis_client: Optional[aioredis.Redis] = None

async def get_redis() -> aioredis.Redis:
    """Get Redis client with connection pooling"""
    global redis_client
    
    if redis_client is None:
        try:
            redis_client = aioredis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                max_connections=settings.REDIS_MAX_CONNECTIONS,
                retry_on_timeout=settings.REDIS_RETRY_ON_TIMEOUT,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                socket_connect_timeout=settings.REDIS_CONNECTION_TIMEOUT,
                decode_responses=True,
                health_check_interval=30,
            )
            
            # Test connection
            await redis_client.ping()
            logger.info("✅ Redis connection established")
            
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {str(e)}")
            redis_client = None
            
    return redis_client

async def close_redis():
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
        logger.info("✅ Redis connection closed")

# Dependency to get database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency function to get database session with proper error handling
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database session error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for database sessions
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Database context error: {str(e)}")
            await session.rollback()
            raise
        finally:
            await session.close()

# Database event listeners for better connection handling
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Set SQLite pragmas for better performance"""
    if "sqlite" in str(dbapi_connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=10000")
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.close()

@event.listens_for(engine.sync_engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Handle connection checkout"""
    logger.debug("Database connection checked out")

@event.listens_for(engine.sync_engine, "checkin")
def receive_checkin(dbapi_connection, connection_record):
    """Handle connection checkin"""
    logger.debug("Database connection checked in")

async def create_tables():
    """
    Create all database tables
    """
    try:
        logger.info("Creating database tables...")
        
        # Import all models to ensure they're registered
        from app.models import user, chat, message, user_preference, emotion
        
        async with engine.begin() as conn:
            # Create all tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {str(e)}")
        raise

async def drop_tables():
    """
    Drop all database tables (for testing)
    """
    try:
        logger.info("Dropping database tables...")
        
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            
        logger.info("✅ Database tables dropped successfully")
        
    except Exception as e:
        logger.error(f"❌ Error dropping database tables: {str(e)}")
        raise

async def check_db_health() -> bool:
    """
    Check database health with comprehensive testing
    """
    try:
        async with AsyncSessionLocal() as session:
            # Test basic connection
            result = await session.execute(text("SELECT 1"))
            await session.commit()
            
            if result.scalar() == 1:
                logger.info("✅ Database health check passed")
                return True
            else:
                logger.error("❌ Database health check failed: unexpected result")
                return False
                
    except Exception as e:
        logger.error(f"❌ Database health check failed: {str(e)}")
        return False

async def check_redis_health() -> bool:
    """
    Check Redis health with comprehensive testing
    """
    try:
        redis = await get_redis()
        if redis is None:
            return False
            
        # Test basic operations
        await redis.ping()
        
        # Test set/get operations
        test_key = "health_check_test"
        await redis.set(test_key, "test_value", ex=10)
        result = await redis.get(test_key)
        await redis.delete(test_key)
        
        if result == "test_value":
            logger.info("✅ Redis health check passed")
            return True
        else:
            logger.error("❌ Redis health check failed: unexpected result")
            return False
            
    except RedisConnectionError as e:
        logger.error(f"❌ Redis connection failed: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ Redis health check failed: {str(e)}")
        return False

async def get_db_stats() -> dict:
    """
    Get database statistics
    """
    try:
        async with AsyncSessionLocal() as session:
            stats = {}
            
            # Connection pool stats
            pool = engine.pool
            stats["pool_size"] = pool.size()
            stats["checked_out_connections"] = pool.checkedout()
            stats["overflow_connections"] = pool.overflow()
            stats["checked_in_connections"] = pool.checkedin()
            
            # Database-specific stats
            if "postgresql" in DATABASE_URL:
                # PostgreSQL specific stats
                result = await session.execute(text("""
                    SELECT 
                        schemaname,
                        tablename,
                        n_tup_ins as inserts,
                        n_tup_upd as updates,
                        n_tup_del as deletes
                    FROM pg_stat_user_tables
                    ORDER BY schemaname, tablename;
                """))
                stats["table_stats"] = [dict(row) for row in result]
            
            return stats
            
    except Exception as e:
        logger.error(f"Error getting database stats: {str(e)}")
        return {"error": str(e)}

async def get_redis_stats() -> dict:
    """
    Get Redis statistics
    """
    try:
        redis = await get_redis()
        if redis is None:
            return {"error": "Redis not available"}
            
        info = await redis.info()
        
        return {
            "connected_clients": info.get("connected_clients", 0),
            "used_memory": info.get("used_memory", 0),
            "used_memory_human": info.get("used_memory_human", "0B"),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "uptime_in_seconds": info.get("uptime_in_seconds", 0),
        }
        
    except Exception as e:
        logger.error(f"Error getting Redis stats: {str(e)}")
        return {"error": str(e)}

# Database utility functions
async def execute_raw_sql(query: str, params: dict = None) -> list:
    """
    Execute raw SQL query with parameters
    """
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text(query), params or {})
            await session.commit()
            return [dict(row) for row in result]
            
    except Exception as e:
        logger.error(f"Error executing raw SQL: {str(e)}")
        raise

async def backup_database():
    """
    Create database backup (implementation depends on database type)
    """
    # This would be implemented based on the specific database type
    # For PostgreSQL, you might use pg_dump
    # For SQLite, you might copy the database file
    logger.info("Database backup functionality not implemented")
    pass

async def cleanup_old_data():
    """
    Clean up old data based on retention policies
    """
    try:
        async with AsyncSessionLocal() as session:
            # Example: Clean up old chat sessions
            cleanup_query = text("""
                DELETE FROM messages 
                WHERE created_at < NOW() - INTERVAL '90 days'
                AND chat_id IN (
                    SELECT id FROM chats 
                    WHERE last_activity_at < NOW() - INTERVAL '90 days'
                )
            """)
            
            result = await session.execute(cleanup_query)
            await session.commit()
            
            logger.info(f"Cleaned up {result.rowcount} old messages")
            
    except Exception as e:
        logger.error(f"Error during data cleanup: {str(e)}")

# Initialize database on module import
async def init_database():
    """
    Initialize database with proper setup
    """
    try:
        await create_tables()
        logger.info("Database initialization completed")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

# Cleanup function for application shutdown
async def cleanup_database():
    """
    Cleanup database connections on shutdown
    """
    try:
        await close_redis()
        await engine.dispose()
        logger.info("Database cleanup completed")
    except Exception as e:
        logger.error(f"Database cleanup failed: {str(e)}")

# Export main components
__all__ = [
    "engine",
    "sync_engine", 
    "AsyncSessionLocal",
    "Base",
    "get_db",
    "get_db_context",
    "get_redis",
    "create_tables",
    "drop_tables",
    "check_db_health",
    "check_redis_health",
    "get_db_stats",
    "get_redis_stats",
    "execute_raw_sql",
    "init_database",
    "cleanup_database"
]
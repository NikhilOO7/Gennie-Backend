from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import asyncio

from app.core.database import get_db, get_redis, test_database_connection, test_redis_connection
from app.core.config import settings
from app.schemas import HealthResponse

router = APIRouter()

@router.get("/", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint"""
    return HealthResponse(
        status="healthy",
        message=f"{settings.project_name} is running",
        timestamp=datetime.utcnow(),
        version=settings.project_version,
        environment=settings.environment
    )

@router.get("/db")
async def database_health_check(db: Session = Depends(get_db)):
    """Check database connectivity and status"""
    try:
        # Test basic database connection
        db.execute("SELECT 1")
        
        # Test table existence
        result = db.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
        table_count = result.scalar()
        
        return {
            "status": "healthy",
            "database": "connected",
            "tables": table_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "database": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/redis")
async def redis_health_check():
    """Check Redis connectivity and status"""
    try:
        redis = await get_redis()
        
        # Test ping
        pong = await redis.ping()
        
        # Test set/get
        test_key = "health_check_test"
        await redis.set(test_key, "test_value", ex=5)  # Expires in 5 seconds
        test_value = await redis.get(test_key)
        await redis.delete(test_key)
        
        # Get Redis info
        info = await redis.info()
        
        return {
            "status": "healthy",
            "redis": "connected",
            "ping": pong,
            "test_successful": test_value == "test_value",
            "redis_version": info.get("redis_version"),
            "connected_clients": info.get("connected_clients"),
            "used_memory_human": info.get("used_memory_human"),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "redis": "disconnected",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

@router.get("/detailed")
async def detailed_health_check(db: Session = Depends(get_db)):
    """Comprehensive health check of all system components"""
    try:
        # Database check
        db_start = datetime.utcnow()
        db.execute("SELECT 1")
        db_time = (datetime.utcnow() - db_start).total_seconds()
        
        # Redis check
        redis_start = datetime.utcnow()
        redis = await get_redis()
        await redis.ping()
        redis_time = (datetime.utcnow() - redis_start).total_seconds()
        
        # System info
    #     import psutil
    #     cpu_percent = psutil.cpu_percent(interval=1)
    #     memory = psutil.virtual_memory()
    #     disk = psutil.disk_usage('/')
        
    #     return {
    #         "status": "healthy",
    #         "timestamp": datetime.utcnow().isoformat(),
    #         "version": settings.project_version,
    #         "environment": settings.environment,
    #         "components": {
    #             "database": {
    #                 "status": "healthy",
    #                 "response_time_seconds": db_time
    #             },
    #             "redis": {
    #                 "status": "healthy",
    #                 "response_time_seconds": redis_time
    #             }
    #         },
    #         "system": {
    #             "cpu_percent": cpu_percent,
    #             "memory_percent": memory.percent,
    #             "disk_percent": (disk.used / disk.total) * 100,
    #             "available_memory_gb": round(memory.available / (1024**3), 2)
    #         }
    #     }
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
        )
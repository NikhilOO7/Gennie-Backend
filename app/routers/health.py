"""
Health Router - System health and monitoring endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from typing import Dict, Any
import logging
import psutil
import os

from app.database import get_db, get_redis, check_db_health, check_redis_health, get_db_stats, get_redis_stats
from app.services.gemini_service import gemini_service
from app.services.emotion_service import emotion_service
from app.services.personalization import personalization_service
from app.config import settings

logger = logging.getLogger(__name__)
health_router = APIRouter()


@health_router.get("/health")
async def health_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Comprehensive health check endpoint"""
    
    start_time = datetime.now(timezone.utc)
    health_status = {
        "status": "healthy",
        "timestamp": start_time.isoformat(),
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "checks": {}
    }
    
    try:
        # Database health check
        db_healthy = await check_db_health()
        health_status["checks"]["database"] = {
            "status": "healthy" if db_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Redis health check
        redis_healthy = await check_redis_health()
        health_status["checks"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Gemini service health check
        gemini_healthy = await gemini_service.health_check()
        health_status["checks"]["gemini"] = {
            "status": "healthy" if gemini_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Emotion service health check
        emotion_healthy = await emotion_service.health_check()
        health_status["checks"]["emotion"] = {
            "status": "healthy" if emotion_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Personalization service health check
        personalization_healthy = await personalization_service.health_check()
        health_status["checks"]["personalization"] = {
            "status": "healthy" if personalization_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Overall status
        all_healthy = all([
            db_healthy,
            redis_healthy,
            gemini_healthy,
            emotion_healthy,
            personalization_healthy
        ])
        
        health_status["status"] = "healthy" if all_healthy else "degraded"
        
        # Add system metrics
        health_status["system"] = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent
        }
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        return health_status


@health_router.get("/health/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    """Database health check"""
    try:
        is_healthy = await check_db_health()
        stats = await get_db_stats(db)
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@health_router.get("/health/redis")
async def redis_health(redis_client = Depends(get_redis)):
    """Redis health check"""
    try:
        is_healthy = await check_redis_health()
        stats = await get_redis_stats(redis_client)
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "stats": stats,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@health_router.get("/health/ai")
async def ai_health():
    """AI services health check"""
    try:
        # Gemini health check
        gemini_healthy = await gemini_service.health_check()
        gemini_info = await gemini_service.get_model_info()
        
        # Emotion service health
        emotion_healthy = await emotion_service.health_check()
        
        # Personalization service health
        personalization_healthy = await personalization_service.health_check()
        
        return {
            "status": "healthy" if all([gemini_healthy, emotion_healthy, personalization_healthy]) else "degraded",
            "services": {
                "gemini": {
                    "status": "healthy" if gemini_healthy else "unhealthy",
                    "model_info": gemini_info
                },
                "emotion": {
                    "status": "healthy" if emotion_healthy else "unhealthy"
                },
                "personalization": {
                    "status": "healthy" if personalization_healthy else "unhealthy"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"AI health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@health_router.get("/metrics")
async def metrics():
    """System metrics endpoint"""
    try:
        cpu_info = {
            "percent": psutil.cpu_percent(interval=1),
            "count": psutil.cpu_count(),
            "count_physical": psutil.cpu_count(logical=False)
        }
        
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        
        network_info = psutil.net_io_counters()
        
        return {
            "system": {
                "cpu": cpu_info,
                "memory": {
                    "total": memory_info.total,
                    "available": memory_info.available,
                    "percent": memory_info.percent,
                    "used": memory_info.used,
                    "free": memory_info.free
                },
                "disk": {
                    "total": disk_info.total,
                    "used": disk_info.used,
                    "free": disk_info.free,
                    "percent": disk_info.percent
                },
                "network": {
                    "bytes_sent": network_info.bytes_sent,
                    "bytes_recv": network_info.bytes_recv,
                    "packets_sent": network_info.packets_sent,
                    "packets_recv": network_info.packets_recv
                }
            },
            "process": {
                "pid": os.getpid(),
                "memory_mb": psutil.Process().memory_info().rss / 1024 / 1024,
                "cpu_percent": psutil.Process().cpu_percent(interval=1)
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }


@health_router.get("/ready")
async def readiness_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Readiness probe for Kubernetes"""
    try:
        # Check all critical services
        db_ready = await check_db_health()
        redis_ready = await check_redis_health()
        gemini_ready = await gemini_service.health_check()
        
        if all([db_ready, redis_ready, gemini_ready]):
            return {"status": "ready"}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )


@health_router.get("/live")
async def liveness_check():
    """Liveness probe for Kubernetes"""
    return {"status": "alive"}
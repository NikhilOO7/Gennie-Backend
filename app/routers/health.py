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
from app.services.openai_service import openai_service
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
            "response_time_ms": 0  # Would measure actual response time
        }
        
        # Redis health check
        redis_healthy = await check_redis_health()
        health_status["checks"]["redis"] = {
            "status": "healthy" if redis_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # OpenAI service health check
        openai_healthy = await openai_service.health_check()
        health_status["checks"]["openai"] = {
            "status": "healthy" if openai_healthy else "unhealthy",
            "response_time_ms": 0
        }
        
        # Emotion service health check
        emotion_healthy = await emotion_service.health_check()
        health_status["checks"]["emotion_service"] = {
            "status": "healthy" if emotion_healthy else "unhealthy"
        }
        
        # Personalization service health check
        personalization_healthy = await personalization_service.health_check()
        health_status["checks"]["personalization_service"] = {
            "status": "healthy" if personalization_healthy else "unhealthy"
        }
        
        # Overall status
        all_healthy = all([
            db_healthy, redis_healthy, openai_healthy, 
            emotion_healthy, personalization_healthy
        ])
        
        health_status["status"] = "healthy" if all_healthy else "degraded"
        
        # Processing time
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        health_status["response_time_seconds"] = processing_time
        
        return health_status
    
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@health_router.get("/health/detailed")
async def detailed_health_check(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Detailed health check with system metrics"""
    
    try:
        # Basic health check
        basic_health = await health_check(db, redis_client)
        
        # System metrics
        system_info = {
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "load_average": os.getloadavg() if hasattr(os, 'getloadavg') else None,
            "process_count": len(psutil.pids())
        }
        
        # Database statistics
        db_stats = await get_db_stats()
        
        # Redis statistics
        redis_stats = await get_redis_stats()
        
        # Service information
        service_info = {
            "openai": openai_service.get_service_stats(),
            "emotion": emotion_service.get_service_info(),
            "personalization": personalization_service.get_service_info()
        }
        
        return {
            **basic_health,
            "system_metrics": system_info,
            "database_stats": db_stats,
            "redis_stats": redis_stats,
            "service_info": service_info
        }
    
    except Exception as e:
        logger.error(f"Detailed health check failed: {str(e)}", exc_info=True)
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

@health_router.get("/health/liveness")
async def liveness_probe():
    """Kubernetes liveness probe endpoint"""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}

@health_router.get("/health/readiness")
async def readiness_probe(
    db: AsyncSession = Depends(get_db),
    redis_client = Depends(get_redis)
):
    """Kubernetes readiness probe endpoint"""
    
    try:
        # Check critical dependencies
        db_healthy = await check_db_health()
        redis_healthy = await check_redis_health()
        
        if db_healthy and redis_healthy:
            return {"status": "ready", "timestamp": datetime.now(timezone.utc).isoformat()}
        else:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service not ready"
            )
    
    except Exception as e:
        logger.error(f"Readiness probe failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready"
        )
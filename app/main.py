"""
Main Application Entry Point - AI Chatbot Backend
FastAPI application with comprehensive middleware, error handling, and lifecycle management
"""

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import sys
from datetime import datetime, timezone
import uvicorn
from typing import Dict, Any

from app.config import settings
from app.database import create_tables, check_db_health, check_redis_health, cleanup_database
from app.routers import auth, users, chat, ai, websocket, health

from app.middleware import (
    RateLimitMiddleware,
    LoggingMiddleware,
    SecurityHeadersMiddleware,
    CompressionMiddleware
)
from app.logger import setup_logging

# Setup logging
logger = setup_logging()

# Application metadata
app_info = {
    "title": "AI Chatbot Backend",
    "description": """
    A production-ready AI-powered conversational backend with:
    - Real-time chat capabilities via WebSocket
    - OpenAI integration for intelligent responses
    - Emotion detection and sentiment analysis
    - User personalization and preference learning
    - Comprehensive authentication and authorization
    - Redis caching for improved performance
    - PostgreSQL for reliable data persistence
    """,
    "version": "2.0.0",
    "contact": {
        "name": "AI Chatbot Team",
        "email": "support@aichatbot.com",
    },
    "license_info": {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifecycle manager
    Handles startup and shutdown operations
    """
    # Startup
    logger.info("🚀 Starting AI Chatbot Backend...")
    
    startup_tasks = []
    
    try:
        # 1. Database setup
        startup_tasks.append("Database initialization")
        await create_tables()
        logger.info("✅ Database tables created/verified")
        
        # 2. Health checks
        startup_tasks.append("Health checks")
        db_healthy = await check_db_health()
        redis_healthy = await check_redis_health()
        
        if db_healthy:
            logger.info("✅ Database connection healthy")
        else:
            logger.error("❌ Database connection failed")
            raise ConnectionError("Database health check failed")
            
        if redis_healthy:
            logger.info("✅ Redis connection healthy")
        else:
            logger.warning("⚠️ Redis connection issues - running in degraded mode")
        
        # 3. Initialize services
        startup_tasks.append("Service initialization")
        from app.services import openai_service, emotion_service, personalization_service
        
        # Test OpenAI connection
        if await openai_service.health_check():
            logger.info("✅ OpenAI service initialized")
        else:
            logger.warning("⚠️ OpenAI service connection issues")
        
        # Initialize emotion service
        if await emotion_service.health_check():
            logger.info("✅ Emotion analysis service initialized")
        else:
            logger.warning("⚠️ Emotion service initialization issues")
        
        # Initialize personalization service
        if await personalization_service.health_check():
            logger.info("✅ Personalization service initialized")
        else:
            logger.warning("⚠️ Personalization service initialization issues")
        
        logger.info("🎉 Application startup complete!")
        logger.info(f"Completed startup tasks: {', '.join(startup_tasks)}")
        
    except Exception as e:
        logger.error(f"❌ Startup failed during {startup_tasks[-1] if startup_tasks else 'initialization'}: {str(e)}")
        raise
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot Backend...")
    
    try:
        await cleanup_database()
        logger.info("✅ Database connections closed")
        
        # Close service connections
        await openai_service.cleanup()
        logger.info("✅ Service connections closed")
        
        logger.info("👋 Application shutdown complete!")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {str(e)}")
        # Don't raise - we want shutdown to complete

# Create FastAPI app
app = FastAPI(
    **app_info,
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"],
)

# Add security headers
app.add_middleware(SecurityHeadersMiddleware)

# Add compression
app.add_middleware(CompressionMiddleware)

# Add trusted host middleware
if settings.ALLOWED_HOSTS:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Add rate limiting
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.RATE_LIMIT_PER_MINUTE
)

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Include routers
app.include_router(auth, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users, prefix="/api/v1/users", tags=["Users"])
app.include_router(chat, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(ai, prefix="/api/v1/ai", tags=["AI"])
app.include_router(websocket, prefix="/api/v1/ws", tags=["WebSocket"])
app.include_router(health, prefix="/health", tags=["Health"])

# Root endpoint
@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - API information"""
    return {
        "name": app_info["title"],
        "version": app_info["version"],
        "status": "running",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "endpoints": {
            "docs": "/docs" if settings.ENVIRONMENT != "production" else None,
            "redoc": "/redoc" if settings.ENVIRONMENT != "production" else None,
            "health": "/health",
            "api": "/api/v1"
        }
    }

# Global exception handlers
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    errors = []
    for error in exc.errors():
        errors.append({
            "field": " -> ".join(str(loc) for loc in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation failed",
            "errors": errors,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions"""
    logger.error(f"Unhandled exception: {str(exc)}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.ENVIRONMENT == "production":
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": "Internal server error",
                "status_code": 500,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url)
            }
        )
    else:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "status_code": 500,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "path": str(request.url)
            }
        )

# Custom middleware for request ID tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to each request for tracking"""
    import uuid
    request_id = str(uuid.uuid4())
    
    # Add to request state
    request.state.request_id = request_id
    
    # Process request
    response = await call_next(request)
    
    # Add to response headers
    response.headers["X-Request-ID"] = request_id
    
    return response

# Performance monitoring endpoint (only in non-production)
if settings.ENVIRONMENT != "production":
    @app.get("/debug/performance", include_in_schema=False)
    async def performance_metrics():
        """Get application performance metrics"""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        
        return {
            "cpu": {
                "percent": process.cpu_percent(interval=0.1),
                "count": psutil.cpu_count()
            },
            "memory": {
                "rss": process.memory_info().rss / 1024 / 1024,  # MB
                "vms": process.memory_info().vms / 1024 / 1024,  # MB
                "percent": process.memory_percent()
            },
            "connections": len(process.connections()),
            "threads": process.num_threads(),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Application runner
if __name__ == "__main__":
    # Configure uvicorn logging
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(client_addr)s - %(request_line)s - %(status_code)s"
    
    # Run the application
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development",
        log_config=log_config,
        access_log=True,
        use_colors=True,
        loop="asyncio",
        workers=1 if settings.ENVIRONMENT == "development" else settings.WORKERS
    )
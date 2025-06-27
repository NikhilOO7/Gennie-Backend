"""
FastAPI Main Application - AI Chatbot Backend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.config import settings
from app.database import create_tables, check_db_health, check_redis_health, engine
from app.routers import auth, users, chat, ai, websocket
from app.routers.health import health_router

# Configure structured logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan event handler with comprehensive startup/shutdown
    """
    # Startup sequence
    logger.info("🚀 Starting AI Chatbot Backend...")
    startup_tasks = []
    
    try:
        # 1. Database initialization
        startup_tasks.append("Database setup")
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
        
        logger.info("🎉 Application startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        # Don't prevent startup for non-critical failures
        logger.warning("⚠️ Some services may be unavailable")
    
    yield  # App runs here
    
    # Shutdown sequence
    logger.info("🔄 Shutting down AI Chatbot Backend...")
    try:
        # Close database connections
        await engine.dispose()
        logger.info("✅ Database connections closed")
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")
    
    logger.info("👋 AI Chatbot Backend shutdown complete")

# Create FastAPI app with lifespan
app = FastAPI(
    title="AI Chatbot Backend",
    description="Production-ready AI-powered conversational backend with real-time chat capabilities",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan
)

# CORS middleware
if settings.ENVIRONMENT == "development":
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Production CORS - more restrictive
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH"],
        allow_headers=["*"],
    )

# Trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global exception on {request.url}: {exc}", exc_info=True)
    
    if settings.ENVIRONMENT == "development":
        # In development, show detailed error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__
            }
        )
    else:
        # In production, hide details
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error"}
        )

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Root endpoint
@app.get("/")
async def root():
    """API root endpoint with system information"""
    return {
        "message": "🤖 AI Chatbot Backend API",
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs_url": "/docs" if settings.ENVIRONMENT != "production" else "Documentation disabled in production",
        "health_check": "/health"
    }

# FIXED: Include all routers with correct references
# The issue was using .router on health when health is already health_router (APIRouter)
app.include_router(health_router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/api/v1/users", tags=["Users"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat Management"])
app.include_router(ai.router, prefix="/api/v1/ai", tags=["AI Conversation"])
app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

# Static files serving (if needed)
if settings.ENVIRONMENT == "development":
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
    except RuntimeError:
        # Static directory doesn't exist, which is fine
        pass

# Note: Startup logic is now handled in the lifespan context manager above
# No need for @app.on_event("startup") as it's deprecated

if __name__ == "__main__":
    import uvicorn
    
    # Development server configuration
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.ENVIRONMENT == "development",
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        reload_dirs=["app"] if settings.ENVIRONMENT == "development" else None
    )
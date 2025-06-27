"""
FastAPI Main Application - AI Chatbot Backend
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
import time
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any

from app.config import settings
from app.database import create_tables, check_db_health, check_redis_health, engine, init_database, cleanup_database
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
        await init_database()
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

# Create FastAPI app with all metadata
app = FastAPI(
    title=settings.APP_NAME,
    description="Advanced AI Chatbot Backend with Voice Processing, Emotion Analysis, and Personalization",
    version=settings.APP_VERSION,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT != "production" else None,
    lifespan=lifespan,
    swagger_ui_parameters={
        "syntaxHighlight.theme": "obsidian",
        "persistAuthorization": True,
    }
)

# Add security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    
    if settings.ENVIRONMENT == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host middleware for production
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware, 
        allowed_hosts=settings.ALLOWED_HOSTS
    )

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # Log slow requests
    if process_time > 1.0:
        logger.warning(f"Slow request: {request.method} {request.url.path} took {process_time:.2f}s")
    
    return response

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # Log request
    logger.info(f"Request: {request.method} {request.url.path} from {request.client.host}")
    
    try:
        response = await call_next(request)
        
        # Log response
        logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
        
        return response
    except Exception as e:
        logger.error(f"Request failed: {request.method} {request.url.path} - {str(e)}")
        raise

# Global exception handlers
@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(f"Database error on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": "Database Error",
            "detail": "A database error occurred" if settings.ENVIRONMENT == "production" else str(exc),
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    
    if settings.ENVIRONMENT == "development":
        # In development, show detailed error
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(exc),
                "type": type(exc).__name__,
                "request_id": getattr(request.state, "request_id", None)
            }
        )
    else:
        # In production, hide details
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "message": "An unexpected error occurred",
                "request_id": getattr(request.state, "request_id", None)
            }
        )

# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint with system information"""
    return {
        "message": "🤖 AI Chatbot Backend API",
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "environment": settings.ENVIRONMENT,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs": {
            "swagger": "/docs" if settings.ENVIRONMENT != "production" else None,
            "redoc": "/redoc" if settings.ENVIRONMENT != "production" else None,
            "openapi": "/openapi.json" if settings.ENVIRONMENT != "production" else None
        },
        "endpoints": {
            "health": "/api/v1/health",
            "auth": "/api/v1/auth",
            "users": "/api/v1/users",
            "chat": "/api/v1/chat",
            "ai": "/api/v1/ai",
            "websocket": "/api/v1/ws"
        }
    }

# API versioning endpoints
@app.get("/api", tags=["Root"])
async def api_versions():
    """List available API versions"""
    return {
        "versions": {
            "v1": {
                "status": "current",
                "base_url": "/api/v1",
                "docs": "/docs"
            }
        },
        "current_version": "v1"
    }

# Include routers with proper prefixes
app.include_router(health_router, prefix="/api/v1", tags=["Health"])
app.include_router(auth, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(users, prefix="/api/v1/users", tags=["Users"])
app.include_router(chat, prefix="/api/v1/chat", tags=["Chat Management"])
app.include_router(ai, prefix="/api/v1/ai", tags=["AI Conversation"])
app.include_router(websocket, prefix="/api/v1/ws", tags=["WebSocket"])

# Static files serving
if settings.ENVIRONMENT == "development":
    try:
        import os
        static_dir = os.path.join(os.path.dirname(__file__), "static")
        if os.path.exists(static_dir):
            app.mount("/static", StaticFiles(directory=static_dir), name="static")
            logger.info("✅ Static files mounted at /static")
    except Exception as e:
        logger.debug(f"Static files not mounted: {e}")

# Add custom OpenAPI schema
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter: Bearer <JWT Token>"
        }
    }
    
    # Add servers for different environments
    openapi_schema["servers"] = [
        {"url": "http://localhost:8000", "description": "Local development server"},
        {"url": "https://api.yourdomain.com", "description": "Production server"}
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

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
        reload_dirs=["app"] if settings.ENVIRONMENT == "development" else None,
        ssl_keyfile=None,  # Add SSL in production
        ssl_certfile=None  # Add SSL in production
    )
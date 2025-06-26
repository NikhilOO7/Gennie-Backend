from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import logging
from datetime import datetime, timezone

from app.config import settings
from app.database import create_tables, check_db_health, check_redis_health
from app.routers import auth, users, chat, ai, websocket

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Modern FastAPI lifespan event handler replacing deprecated on_event
    """
    # Startup
    logger.info("🚀 Starting AI Chatbot Backend...")
    try:
        # Create database tables
        await create_tables()
        logger.info("✅ Database tables created/verified")
        
        # Check database health
        if check_db_health():
            logger.info("✅ Database connection healthy")
        else:
            logger.warning("⚠️ Database connection issues detected")
            
        # Check Redis health
        if check_redis_health():
            logger.info("✅ Redis connection healthy")
        else:
            logger.warning("⚠️ Redis connection issues detected")
            
        logger.info("🎉 Application startup complete!")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {str(e)}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot Backend...")
    logger.info("👋 Application shutdown complete!")

# Create FastAPI app with lifespan
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    description="Advanced AI Chatbot Backend API with Modern FastAPI Standards",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan  # Modern lifespan replacement for on_event
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if settings.DEBUG else ["yourdomain.com"]
)

# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# Include routers
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(chat.router)
app.include_router(ai.router)
app.include_router(websocket.router)

# Health check endpoints
@app.get("/health")
async def health_check():
    """Health check endpoint with modern datetime handling"""
    db_healthy = check_db_health()
    redis_healthy = check_redis_health()
    
    status = "healthy" if db_healthy and redis_healthy else "unhealthy"
    
    return {
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),  # Modern timezone-aware datetime
        "version": settings.VERSION,
        "services": {
            "database": "healthy" if db_healthy else "unhealthy",
            "redis": "healthy" if redis_healthy else "unhealthy"
        }
    }

@app.get("/")
async def root():
    """Root endpoint with modern datetime"""
    return {
        "message": f"Welcome to {settings.APP_NAME}",
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "docs_url": "/docs" if settings.DEBUG else "Contact admin for API documentation"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )
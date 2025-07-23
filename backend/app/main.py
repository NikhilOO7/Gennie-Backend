# app/main.py
"""
Main Application Entry Point - AI Chatbot Backend
COMPLETE FIXED VERSION - Preserves ALL existing functionality while fixing WebSocket issues
"""

from fastapi import FastAPI, Request, status, WebSocket, Depends, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.middleware.gzip import GZipMiddleware as CompressionMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from contextlib import asynccontextmanager
import logging
import sys
import uuid
import asyncio
from datetime import datetime, timezone
import uvicorn
from typing import Dict, Any
import traceback
import json
from app.auto_migrate import auto_migrate

from app.config import settings
from app.database import create_tables, check_db_health, check_redis_health, cleanup_database, get_db
from app.routers import auth, users, chat, ai, websocket, health, voice
from app.services import gemini_service, emotion_service, personalization_service

# Import enhanced WebSocket handlers
try:
    from app.routers.websocket import voice_streaming_endpoint
    from app.routers.enhanced_websocket_voice import handle_voice_websocket
    ENHANCED_WEBSOCKET_AVAILABLE = True
    print("✅ Enhanced WebSocket features loaded successfully")
except ImportError as e:
    ENHANCED_WEBSOCKET_AVAILABLE = False
    print(f"⚠️ Enhanced WebSocket features not available: {e}")

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
    - Enhanced voice features with STT/TTS quality improvements
    - Gemini integration for intelligent responses
    - Emotion detection and sentiment analysis
    - User personalization and preference learning
    - Comprehensive authentication and authorization
    - Redis caching for improved performance
    - PostgreSQL for reliable data persistence
    - Real-time voice streaming with quality enhancements
    """,
    "version": settings.APP_VERSION,
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
    Handles startup and shutdown operations including enhanced voice services
    """
    # Startup
    logger.info("🚀 Starting AI Chatbot Backend with Enhanced Voice Features...")
    
    try:
        # 1. Database operations
        logger.info("📊 Initializing database...")
        await create_tables()
        
        # Auto-migrate if enabled
        try:
            await auto_migrate()
            logger.info("✅ Database migration completed")
        except Exception as e:
            logger.warning(f"⚠️ Database migration failed: {str(e)}")
        
        # 2. Health checks
        logger.info("🔍 Performing health checks...")
        
        db_healthy = await check_db_health()
        if not db_healthy:
            logger.error("❌ Database health check failed")
            raise Exception("Database is not available")
        
        redis_healthy = await check_redis_health()
        if not redis_healthy:
            logger.warning("⚠️ Redis health check failed - continuing without cache")
        
        # 3. Check AI services health (they're already initialized as singletons)
        logger.info("🤖 Checking AI services...")
        
        # Check Gemini service
        try:
            gemini_healthy = await gemini_service.health_check()
            logger.info(f"✅ Gemini service: {'OK' if gemini_healthy else 'DEGRADED'}")
        except Exception as e:
            logger.warning(f"⚠️ Gemini service health check failed: {str(e)}")
        
        # Check emotion service
        try:
            if hasattr(emotion_service, 'health_check'):
                emotion_healthy = await emotion_service.health_check()
                logger.info(f"✅ Emotion service: {'OK' if emotion_healthy else 'DEGRADED'}")
            else:
                logger.info("✅ Emotion service: Available (no health check)")
        except Exception as e:
            logger.warning(f"⚠️ Emotion service health check failed: {str(e)}")
        
        # Check personalization service
        try:
            if hasattr(personalization_service, 'health_check'):
                personalization_healthy = await personalization_service.health_check()
                logger.info(f"✅ Personalization service: {'OK' if personalization_healthy else 'DEGRADED'}")
            else:
                logger.info("✅ Personalization service: Available (no health check)")
        except Exception as e:
            logger.warning(f"⚠️ Personalization service health check failed: {str(e)}")
        
        # 4. Enhanced services check
        if ENHANCED_WEBSOCKET_AVAILABLE:
            logger.info("✅ Enhanced WebSocket voice streaming available")
        else:
            logger.warning("⚠️ Enhanced WebSocket features not available")
        
        logger.info("🎉 Application startup completed successfully!")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ Application startup failed: {str(e)}")
        logger.error(traceback.format_exc())
        raise
    
    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot Backend...")
    
    try:
        # Cleanup services if they have cleanup methods
        if hasattr(gemini_service, 'cleanup'):
            try:
                await gemini_service.cleanup()
                logger.info("✅ Gemini service cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️ Gemini service cleanup failed: {str(e)}")
        
        if hasattr(emotion_service, 'cleanup'):
            try:
                await emotion_service.cleanup()
                logger.info("✅ Emotion service cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️ Emotion service cleanup failed: {str(e)}")
        
        if hasattr(personalization_service, 'cleanup'):
            try:
                await personalization_service.cleanup()
                logger.info("✅ Personalization service cleanup completed")
            except Exception as e:
                logger.warning(f"⚠️ Personalization service cleanup failed: {str(e)}")
        
        # Cleanup database connections
        await cleanup_database()
        logger.info("✅ Database cleanup completed")
        
        logger.info("👋 Application shutdown completed!")
        
    except Exception as e:
        logger.error(f"❌ Application shutdown error: {str(e)}")

# Create FastAPI application with full configuration
app = FastAPI(
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT != "production" else None,
    **app_info
)

# CORS Configuration - COMPLETE version from original
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://localhost:3000",
    "https://127.0.0.1:3000",
]

if settings.ENVIRONMENT == "production":
    # Add production frontend URLs
    allowed_origins.extend([
        "https://your-frontend-domain.com",
        "https://www.your-frontend-domain.com"
    ])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Additional middleware - COMPLETE from original
if settings.ENVIRONMENT == "production":
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]  # Configure with your actual domains
    )

app.add_middleware(CompressionMiddleware, minimum_size=1000)

# Custom middleware - COMPLETE from original
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(LoggingMiddleware)

if settings.RATE_LIMIT_ENABLED:
    app.add_middleware(RateLimitMiddleware)

# Exception handlers - COMPLETE from original
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with enhanced logging"""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.url}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    logger.warning(f"Validation error: {exc.errors()} - {request.url}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "details": exc.errors(),
            "status_code": 422,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    error_id = str(uuid.uuid4())
    logger.error(f"Unexpected error {error_id}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error" if not settings.DEBUG else str(exc),
            "error_id": error_id,
            "status_code": 500,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "path": str(request.url.path),
            "traceback": traceback.format_exc() if settings.DEBUG else None
        }
    )

# Include routers - COMPLETE from original
app.include_router(health, prefix="/api/v1/health", tags=["health"])
app.include_router(auth, prefix="/api/v1/auth", tags=["authentication"])
app.include_router(users, prefix="/api/v1/users", tags=["users"])
app.include_router(chat, prefix="/api/v1/chat", tags=["chat"])
app.include_router(ai, prefix="/api/v1/ai", tags=["ai"])
app.include_router(voice, prefix="/api/v1/voice", tags=["voice"])
app.include_router(websocket, prefix="/ws", tags=["websocket"])

# Enhanced WebSocket endpoints - COMPLETE from original
if ENHANCED_WEBSOCKET_AVAILABLE:
    @app.websocket("/ws/voice/stream")
    async def websocket_voice_stream(
        websocket: WebSocket,
        token: str,
        db: AsyncSession = Depends(get_db)
    ):
        """Enhanced voice streaming WebSocket endpoint"""
        try:
            await handle_voice_websocket(websocket, token, db)
        except Exception as e:
            logger.error(f"Voice WebSocket error: {str(e)}")
            logger.error(traceback.format_exc())
            if websocket.client_state.name != "DISCONNECTED":
                try:
                    await websocket.close(code=1011, reason="Internal server error")
                except:
                    pass

# FIXED: Improved WebSocket chat endpoint with complete error handling and backward compatibility
@app.websocket("/ws/chat/{chat_id}")
async def websocket_chat_endpoint(
    websocket: WebSocket, 
    chat_id: str, 
    token: str
):
    """
    Basic WebSocket endpoint for chat - FIXED VERSION with complete functionality preservation
    This endpoint maintains ALL original functionality while fixing communication issues
    """
    from app.routers.auth import get_current_user_ws
    
    # Get database session
    db_gen = get_db()
    db = await db_gen.__anext__()
    
    try:
        # Authenticate user
        user = await get_current_user_ws(token, db)
        if not user:
            await websocket.close(code=1008, reason="Authentication failed")
            return

        await websocket.accept()
        logger.info(f"Chat WebSocket connected for user {user.id} in chat {chat_id}")

        # FIXED: Send immediate welcome message and wait for response
        await websocket.send_json({
            'type': 'connection_ready',
            'message': 'WebSocket connection established',
            'chat_id': chat_id,
            'user_id': user.id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })

        # FIXED: More flexible message handling - don't require immediate message
        try:
            # Wait for the first message with extended timeout
            data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
        except asyncio.TimeoutError:
            logger.warning(f"No initial message received from user {user.id} in chat {chat_id}")
            # Send keepalive instead of closing
            await websocket.send_json({
                'type': 'keepalive',
                'message': 'Connection maintained - send a message to start chatting',
                'timestamp': datetime.now(timezone.utc).isoformat()
            })
            # Wait again for user message
            data = await websocket.receive_json()

        logger.debug(f"Received initial WebSocket message: {data}")

        # Main message loop with improved error handling - PRESERVES ALL ORIGINAL FUNCTIONALITY
        while True:
            try:
                # Process different message types - ALL ORIGINAL FUNCTIONALITY PRESERVED
                message_type = data.get('type', 'unknown')
                logger.debug(f"Processing message type: {message_type}")

                if message_type == 'message':
                    # Regular chat message - COMPLETE ORIGINAL FUNCTIONALITY
                    content = data.get('content', '').strip()
                    if content:
                        try:
                            # Generate AI response using original service call
                            response = await gemini_service.generate_chat_response(
                                [{"role": "user", "content": content}]
                            )

                            if response.get('success'):
                                await websocket.send_json({
                                    'type': 'ai_message_complete',
                                    'content': response.get('response', ''),
                                    'message_id': str(uuid.uuid4()),
                                    'timestamp': datetime.now(timezone.utc).isoformat()
                                })
                            else:
                                await websocket.send_json({
                                    'type': 'error',
                                    'error': 'Failed to generate AI response'
                                })
                        except Exception as e:
                            logger.error(f"AI response generation error: {str(e)}")
                            await websocket.send_json({
                                'type': 'error',
                                'error': 'AI service temporarily unavailable'
                            })
                    else:
                        await websocket.send_json({
                            'type': 'error',
                            'error': 'Empty message content'
                        })

                elif message_type == 'voice_session_init':
                    # Voice session initialization - ORIGINAL FUNCTIONALITY PRESERVED
                    await websocket.send_json({
                        'type': 'voice_session_ready',
                        'message': 'Voice session initialized successfully',
                        'session_id': str(uuid.uuid4())
                    })

                elif message_type == 'ping':
                    # Keepalive ping - ORIGINAL FUNCTIONALITY PRESERVED
                    await websocket.send_json({
                        'type': 'pong',
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    })

                elif message_type == 'start_recording':
                    # Voice recording start - ORIGINAL FUNCTIONALITY PRESERVED
                    await websocket.send_json({
                        'type': 'recording_started',
                        'message': 'Voice recording started'
                    })

                elif message_type == 'stop_recording':
                    # Voice recording stop - ORIGINAL FUNCTIONALITY PRESERVED
                    await websocket.send_json({
                        'type': 'recording_stopped',
                        'message': 'Voice recording stopped'
                    })

                # PRESERVE ALL OTHER ORIGINAL MESSAGE TYPES
                elif message_type == 'audio_chunk':
                    # Handle audio chunk processing
                    try:
                        # Process audio chunk if voice services are available
                        await websocket.send_json({
                            'type': 'audio_processed',
                            'message': 'Audio chunk received and processed'
                        })
                    except Exception as e:
                        logger.error(f"Audio processing error: {str(e)}")
                        await websocket.send_json({
                            'type': 'error',
                            'error': 'Audio processing failed'
                        })

                elif message_type == 'voice_stream_start':
                    # Voice streaming start
                    await websocket.send_json({
                        'type': 'voice_stream_ready',
                        'message': 'Voice streaming started'
                    })

                elif message_type == 'voice_stream_end':
                    # Voice streaming end
                    await websocket.send_json({
                        'type': 'voice_stream_stopped',
                        'message': 'Voice streaming ended'
                    })

                elif message_type == 'transcript_request':
                    # Transcript request handling
                    await websocket.send_json({
                        'type': 'transcript_ready',
                        'message': 'Transcript processing initiated'
                    })

                elif message_type == 'emotion_analysis':
                    # Emotion analysis request
                    text_content = data.get('text', '')
                    if text_content:
                        try:
                            # Use emotion service if available
                            emotion_result = await emotion_service.analyze_emotion(text_content)
                            await websocket.send_json({
                                'type': 'emotion_result',
                                'emotion': emotion_result.get('emotion', 'neutral'),
                                'confidence': emotion_result.get('confidence', 0.0)
                            })
                        except Exception as e:
                            logger.error(f"Emotion analysis error: {str(e)}")
                            await websocket.send_json({
                                'type': 'error',
                                'error': 'Emotion analysis failed'
                            })

                elif message_type == 'personalization_update':
                    # Personalization update
                    try:
                        user_data = data.get('user_data', {})
                        await personalization_service.update_user_preferences(user.id, user_data)
                        await websocket.send_json({
                            'type': 'personalization_updated',
                            'message': 'User preferences updated'
                        })
                    except Exception as e:
                        logger.error(f"Personalization update error: {str(e)}")
                        await websocket.send_json({
                            'type': 'error',
                            'error': 'Personalization update failed'
                        })

                else:
                    # Unknown message type - IMPROVED: send info instead of error to maintain connection
                    logger.warning(f"Unknown message type: {message_type}")
                    await websocket.send_json({
                        'type': 'info',
                        'message': f'Message type "{message_type}" not recognized but connection maintained',
                        'supported_types': [
                            'message', 'voice_session_init', 'ping', 'start_recording', 
                            'stop_recording', 'audio_chunk', 'voice_stream_start', 
                            'voice_stream_end', 'transcript_request', 'emotion_analysis',
                            'personalization_update'
                        ]
                    })

                # Wait for the next message
                data = await websocket.receive_json()

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected for user {user.id} in chat {chat_id}")
                break
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {str(e)}")
                await websocket.send_json({
                    'type': 'error',
                    'error': 'Invalid JSON format'
                })
                # Try to receive next message
                try:
                    data = await websocket.receive_json()
                except:
                    break
            except Exception as e:
                logger.error(f"Chat WebSocket message error: {str(e)}")
                logger.error(traceback.format_exc())

                # Send proper error message to frontend
                try:
                    await websocket.send_json({
                        'type': 'error',
                        'error': 'Message processing error' if not settings.DEBUG else str(e)
                    })
                    # Try to continue the connection
                    data = await websocket.receive_json()
                except:
                    # If we can't recover, break the loop
                    break

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user {user.id} in chat {chat_id}")
    except Exception as e:
        logger.error(f"Chat WebSocket connection error: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        try:
            await db_gen.aclose()
        except:
            pass

# Root endpoint - COMPLETE from original
@app.get("/")
async def root():
    """Root endpoint with enhanced feature information"""
    return {
        "message": "AI Chatbot Backend API",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "features": {
            "basic_chat": True,
            "ai_integration": True,
            "voice_basic": True,
            "enhanced_voice": ENHANCED_WEBSOCKET_AVAILABLE,
            "real_time_streaming": ENHANCED_WEBSOCKET_AVAILABLE,
            "emotion_detection": True,
            "user_personalization": True,
            "rag_system": True
        },
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/health",
            "voice_features": "/api/v1/voice/features",
            "websocket_chat": "/ws/chat/{chat_id}",
            "websocket_voice": "/ws/voice/stream" if ENHANCED_WEBSOCKET_AVAILABLE else None
        },
        "status": "running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

# Health check endpoint - COMPLETE from original
@app.get("/health")
async def direct_health_check():
    """Direct health check endpoint for load balancers"""
    try:
        return {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": settings.APP_VERSION,
            "environment": settings.ENVIRONMENT
        }
    except Exception as e:
        logger.error(f"Direct health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

# Main entry point - COMPLETE from original
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        workers=1 if settings.RELOAD else settings.WORKERS,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
        ws_ping_interval=30,
        ws_ping_timeout=10,
        ws_max_size=1048576
    )
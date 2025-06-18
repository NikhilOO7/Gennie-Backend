from fastapi import APIRouter
from app.api.v1.endpoints import health, chat, ai

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health Check"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat Management"]
)

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Conversation"]
)

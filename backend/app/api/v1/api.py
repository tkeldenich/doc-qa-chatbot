from fastapi import APIRouter

from app.api.v1.endpoints import auth, chat, documents, health, users

api_router = APIRouter()

# Include all routers
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(
    documents.router, prefix="/documents", tags=["documents"]
)
api_router.include_router(chat.router, prefix="/chat", tags=["chat"])

from fastapi import APIRouter

router = APIRouter()


@router.get("/ping")
async def ping():
    """Simple health check endpoint."""
    return {"message": "pong", "status": "healthy"}


@router.get("/info")
async def info():
    """API information."""
    return {
        "name": "Document Q&A Chatbot API",
        "version": "0.1.0",
        "status": "running",
    }

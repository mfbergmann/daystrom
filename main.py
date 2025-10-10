"""Main FastAPI application entry point."""
from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import init_db, get_db
from app.bot.telegram_handler import telegram_handler
from app.scheduler import task_scheduler
from config import settings
from loguru import logger
import sys

# Configure logging
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add("logs/daystrom.log", rotation="1 day", retention="7 days", level="DEBUG")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for startup and shutdown."""
    # Startup
    logger.info("Starting Daystrom application")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start scheduler
    task_scheduler.start()
    logger.info("Task scheduler started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Daystrom application")
    task_scheduler.stop()


# Create FastAPI app
app = FastAPI(
    title="Daystrom",
    description="AI-Powered Personal Memory & Task Assistant",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Daystrom",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Telegram webhook endpoint."""
    try:
        update_data = await request.json()
        await telegram_handler.process_webhook(update_data)
        return JSONResponse({"status": "ok"})
    except Exception as e:
        logger.error(f"Error processing Telegram webhook: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/auth/google/authorize")
async def google_authorize(user_id: int, db: AsyncSession = Depends(get_db)):
    """Initiate Google Calendar OAuth flow."""
    from app.services.calendar_service import calendar_service
    
    try:
        auth_url = await calendar_service.get_google_auth_url(user_id)
        return {"authorization_url": auth_url}
    except Exception as e:
        logger.error(f"Error initiating Google auth: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/auth/google/callback")
async def google_callback(
    state: str,
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """Handle Google Calendar OAuth callback."""
    from app.services.calendar_service import calendar_service
    
    try:
        user_id = int(state)
        await calendar_service.handle_google_callback(db, user_id, code)
        return {"status": "success", "message": "Google Calendar connected successfully"}
    except Exception as e:
        logger.error(f"Error handling Google callback: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting server on {settings.app_host}:{settings.app_port}")
    uvicorn.run(
        "main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug
    )


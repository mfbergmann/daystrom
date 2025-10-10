"""Background task scheduler for digests and reminders."""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select
from telegram import Bot
from datetime import datetime, timedelta
from typing import List

from app.models import User, Item
from app.database import AsyncSessionLocal
from app.services.openai_service import openai_service
from app.services.memory_service import memory_service
from app.services.calendar_service import calendar_service
from config import settings
from loguru import logger


class TaskScheduler:
    """Scheduler for background tasks."""
    
    def __init__(self):
        """Initialize scheduler."""
        self.scheduler = AsyncIOScheduler(timezone=settings.timezone)
        self.bot = Bot(token=settings.telegram_bot_token)
    
    def start(self):
        """Start the scheduler."""
        # Schedule daily digests
        hour, minute = settings.digest_time_daily.split(':')
        self.scheduler.add_job(
            self.send_daily_digests,
            CronTrigger(hour=int(hour), minute=int(minute)),
            id='daily_digests'
        )
        
        # Schedule weekly digests (Monday)
        hour, minute = settings.digest_time_weekly.split(':')
        self.scheduler.add_job(
            self.send_weekly_digests,
            CronTrigger(day_of_week='mon', hour=int(hour), minute=int(minute)),
            id='weekly_digests'
        )
        
        # Schedule calendar sync every hour
        self.scheduler.add_job(
            self.sync_calendars,
            CronTrigger(minute=0),
            id='calendar_sync'
        )
        
        self.scheduler.start()
        logger.info("Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    async def send_daily_digests(self):
        """Send daily digests to all users with digests enabled."""
        logger.info("Starting daily digest generation")
        
        try:
            async with AsyncSessionLocal() as db:
                # Get all users with digests enabled
                stmt = select(User).where(User.digest_enabled == True)
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                for user in users:
                    try:
                        await self._send_digest_to_user(db, user, period='daily')
                    except Exception as e:
                        logger.error(f"Error sending digest to user {user.telegram_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in daily digest job: {e}")
    
    async def send_weekly_digests(self):
        """Send weekly digests to all users with weekly digests enabled."""
        logger.info("Starting weekly digest generation")
        
        try:
            async with AsyncSessionLocal() as db:
                # Get all users with weekly digests enabled
                stmt = select(User).where(User.weekly_digest_enabled == True)
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                for user in users:
                    try:
                        await self._send_digest_to_user(db, user, period='weekly')
                    except Exception as e:
                        logger.error(f"Error sending weekly digest to user {user.telegram_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in weekly digest job: {e}")
    
    async def _send_digest_to_user(self, db, user: User, period: str = 'daily'):
        """Send digest to a specific user."""
        days = 1 if period == 'daily' else 7
        
        # Get recent items
        items = await memory_service.get_recent_items(
            db, user.id, days=days, completed=False
        )
        
        if not items:
            return  # Don't send empty digests
        
        # Get upcoming calendar events
        hours = 24 if period == 'daily' else 168  # 7 days
        calendar_events = await calendar_service.get_upcoming_events(
            db, user.id, hours=hours
        )
        
        # Prepare data
        items_data = [
            {
                'content': item.content,
                'item_type': item.item_type,
                'due_date': item.due_date.isoformat() if item.due_date else None,
                'tags': item.tags or [],
                'priority': item.priority
            }
            for item in items[:30]
        ]
        
        events_data = [
            {
                'title': event.title,
                'start_time': event.start_time.isoformat(),
                'location': event.location
            }
            for event in calendar_events
        ]
        
        # Generate digest
        digest = await openai_service.generate_digest(items_data, events_data)
        
        # Send via Telegram
        message = f"{'📅 Daily' if period == 'daily' else '📊 Weekly'} Digest\n\n{digest}"
        
        await self.bot.send_message(
            chat_id=user.telegram_id,
            text=message
        )
        
        logger.info(f"Sent {period} digest to user {user.telegram_id}")
    
    async def sync_calendars(self):
        """Sync calendars for all users with calendar integration enabled."""
        logger.info("Starting calendar sync")
        
        try:
            async with AsyncSessionLocal() as db:
                # Get users with calendar integration
                stmt = select(User).where(
                    (User.google_calendar_enabled == True) | (User.caldav_enabled == True)
                )
                result = await db.execute(stmt)
                users = result.scalars().all()
                
                for user in users:
                    try:
                        if user.google_calendar_enabled:
                            await calendar_service.sync_google_calendar(db, user.id)
                            logger.info(f"Synced Google Calendar for user {user.telegram_id}")
                        
                        if user.caldav_enabled:
                            await calendar_service.sync_caldav_calendar(db, user.id)
                            logger.info(f"Synced CalDAV calendar for user {user.telegram_id}")
                            
                    except Exception as e:
                        logger.error(f"Error syncing calendar for user {user.telegram_id}: {e}")
                
        except Exception as e:
            logger.error(f"Error in calendar sync job: {e}")


# Global instance
task_scheduler = TaskScheduler()


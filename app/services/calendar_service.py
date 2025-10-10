"""Calendar service for Google Calendar and CalDAV integration."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import caldav
from caldav.elements import dav, cdav
from app.models import CalendarEvent, User
from config import settings
from loguru import logger


class CalendarService:
    """Service for calendar integration."""
    
    def __init__(self):
        """Initialize calendar service."""
        self.google_scopes = ['https://www.googleapis.com/auth/calendar.readonly']
    
    async def get_google_auth_url(self, user_id: int) -> str:
        """
        Generate Google OAuth URL for calendar access.
        
        Args:
            user_id: User ID for state parameter
            
        Returns:
            Authorization URL
        """
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [settings.google_redirect_uri]
                    }
                },
                scopes=self.google_scopes,
                redirect_uri=settings.google_redirect_uri
            )
            
            authorization_url, state = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=str(user_id)
            )
            
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error generating Google auth URL: {e}")
            raise
    
    async def handle_google_callback(
        self,
        db: AsyncSession,
        user_id: int,
        code: str
    ):
        """
        Handle Google OAuth callback and store refresh token.
        
        Args:
            db: Database session
            user_id: User ID
            code: Authorization code
        """
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": settings.google_client_id,
                        "client_secret": settings.google_client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [settings.google_redirect_uri]
                    }
                },
                scopes=self.google_scopes,
                redirect_uri=settings.google_redirect_uri
            )
            
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Store refresh token
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one()
            
            user.google_calendar_refresh_token = credentials.refresh_token
            user.google_calendar_enabled = True
            
            await db.commit()
            
        except Exception as e:
            logger.error(f"Error handling Google callback: {e}")
            await db.rollback()
            raise
    
    async def sync_google_calendar(
        self,
        db: AsyncSession,
        user_id: int,
        days_ahead: int = 7
    ) -> List[CalendarEvent]:
        """
        Sync events from Google Calendar.
        
        Args:
            db: Database session
            user_id: User ID
            days_ahead: Number of days to fetch ahead
            
        Returns:
            List of synced events
        """
        try:
            # Get user's refresh token
            stmt = select(User).where(User.id == user_id)
            result = await db.execute(stmt)
            user = result.scalar_one()
            
            if not user.google_calendar_enabled or not user.google_calendar_refresh_token:
                return []
            
            # Build credentials
            credentials = Credentials(
                token=None,
                refresh_token=user.google_calendar_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret
            )
            
            # Build service
            service = build('calendar', 'v3', credentials=credentials)
            
            # Calculate time range
            now = datetime.utcnow()
            time_min = now.isoformat() + 'Z'
            time_max = (now + timedelta(days=days_ahead)).isoformat() + 'Z'
            
            # Fetch events
            events_result = service.events().list(
                calendarId='primary',
                timeMin=time_min,
                timeMax=time_max,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            
            events = events_result.get('items', [])
            
            synced_events = []
            for event in events:
                # Parse event data
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                
                # Check if event exists
                stmt = select(CalendarEvent).where(
                    and_(
                        CalendarEvent.user_id == user_id,
                        CalendarEvent.external_id == event['id'],
                        CalendarEvent.source == 'google'
                    )
                )
                result = await db.execute(stmt)
                cal_event = result.scalar_one_or_none()
                
                if cal_event:
                    # Update existing
                    cal_event.title = event.get('summary', 'Untitled')
                    cal_event.description = event.get('description')
                    cal_event.location = event.get('location')
                    cal_event.start_time = datetime.fromisoformat(start.replace('Z', '+00:00'))
                    cal_event.end_time = datetime.fromisoformat(end.replace('Z', '+00:00'))
                    cal_event.synced_at = datetime.utcnow()
                else:
                    # Create new
                    cal_event = CalendarEvent(
                        user_id=user_id,
                        external_id=event['id'],
                        source='google',
                        title=event.get('summary', 'Untitled'),
                        description=event.get('description'),
                        location=event.get('location'),
                        start_time=datetime.fromisoformat(start.replace('Z', '+00:00')),
                        end_time=datetime.fromisoformat(end.replace('Z', '+00:00')),
                        all_day='date' in event['start']
                    )
                    db.add(cal_event)
                
                synced_events.append(cal_event)
            
            await db.commit()
            return synced_events
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Error syncing Google Calendar: {e}")
            await db.rollback()
            raise
    
    async def sync_caldav_calendar(
        self,
        db: AsyncSession,
        user_id: int,
        days_ahead: int = 7
    ) -> List[CalendarEvent]:
        """
        Sync events from CalDAV (Apple Calendar).
        
        Args:
            db: Database session
            user_id: User ID
            days_ahead: Number of days to fetch ahead
            
        Returns:
            List of synced events
        """
        if not settings.caldav_url or not settings.caldav_username or not settings.caldav_password:
            logger.warning("CalDAV credentials not configured")
            return []
        
        try:
            # Connect to CalDAV server
            client = caldav.DAVClient(
                url=settings.caldav_url,
                username=settings.caldav_username,
                password=settings.caldav_password
            )
            
            principal = client.principal()
            calendars = principal.calendars()
            
            if not calendars:
                logger.warning("No calendars found in CalDAV account")
                return []
            
            # Use first calendar
            calendar = calendars[0]
            
            # Calculate time range
            now = datetime.utcnow()
            end_date = now + timedelta(days=days_ahead)
            
            # Fetch events
            events = calendar.date_search(
                start=now,
                end=end_date,
                expand=True
            )
            
            synced_events = []
            for event in events:
                try:
                    ical = event.icalendar_component
                    
                    # Extract event details
                    summary = str(ical.get('summary', 'Untitled'))
                    description = str(ical.get('description', ''))
                    location = str(ical.get('location', ''))
                    dtstart = ical.get('dtstart').dt
                    dtend = ical.get('dtend').dt
                    uid = str(ical.get('uid'))
                    
                    # Convert to datetime if date
                    if isinstance(dtstart, datetime):
                        start_time = dtstart
                        end_time = dtend
                        all_day = False
                    else:
                        start_time = datetime.combine(dtstart, datetime.min.time())
                        end_time = datetime.combine(dtend, datetime.min.time())
                        all_day = True
                    
                    # Check if event exists
                    stmt = select(CalendarEvent).where(
                        and_(
                            CalendarEvent.user_id == user_id,
                            CalendarEvent.external_id == uid,
                            CalendarEvent.source == 'caldav'
                        )
                    )
                    result = await db.execute(stmt)
                    cal_event = result.scalar_one_or_none()
                    
                    if cal_event:
                        # Update existing
                        cal_event.title = summary
                        cal_event.description = description
                        cal_event.location = location
                        cal_event.start_time = start_time
                        cal_event.end_time = end_time
                        cal_event.synced_at = datetime.utcnow()
                    else:
                        # Create new
                        cal_event = CalendarEvent(
                            user_id=user_id,
                            external_id=uid,
                            source='caldav',
                            title=summary,
                            description=description,
                            location=location,
                            start_time=start_time,
                            end_time=end_time,
                            all_day=all_day
                        )
                        db.add(cal_event)
                    
                    synced_events.append(cal_event)
                    
                except Exception as e:
                    logger.error(f"Error processing CalDAV event: {e}")
                    continue
            
            await db.commit()
            return synced_events
            
        except Exception as e:
            logger.error(f"Error syncing CalDAV calendar: {e}")
            await db.rollback()
            raise
    
    async def get_upcoming_events(
        self,
        db: AsyncSession,
        user_id: int,
        hours: int = 24
    ) -> List[CalendarEvent]:
        """
        Get upcoming events for a user.
        
        Args:
            db: Database session
            user_id: User ID
            hours: Number of hours to look ahead
            
        Returns:
            List of upcoming events
        """
        now = datetime.utcnow()
        future = now + timedelta(hours=hours)
        
        stmt = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time >= now,
                CalendarEvent.start_time <= future
            )
        ).order_by(CalendarEvent.start_time)
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def check_time_available(
        self,
        db: AsyncSession,
        user_id: int,
        start_time: datetime,
        duration_minutes: int = 60
    ) -> bool:
        """
        Check if a time slot is available (no conflicts).
        
        Args:
            db: Database session
            user_id: User ID
            start_time: Proposed start time
            duration_minutes: Duration in minutes
            
        Returns:
            True if time is available
        """
        end_time = start_time + timedelta(minutes=duration_minutes)
        
        stmt = select(CalendarEvent).where(
            and_(
                CalendarEvent.user_id == user_id,
                CalendarEvent.start_time < end_time,
                CalendarEvent.end_time > start_time
            )
        )
        
        result = await db.execute(stmt)
        conflicts = result.scalars().all()
        
        return len(conflicts) == 0


# Global instance
calendar_service = CalendarService()


"""Telegram bot handler for Daystrom AI Assistant."""
import asyncio
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot, Update
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes,
)
from loguru import logger

from config import settings
from app.models.user import User
from app.services.memory_service import memory_service
from app.services.openai_service import openai_service
from app.services.calendar_service import calendar_service


class TelegramHandler:
    """Handler for Telegram bot interactions."""
    
    def __init__(self):
        """Initialize Telegram bot."""
        # Create Application which manages the bot instance
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Register handlers
        self._register_handlers()
    
    @property
    def bot(self):
        """Get the bot instance from the application."""
        return self.application.bot

    def _register_handlers(self):
        """Register command and message handlers."""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("digest", self.digest_command))
        self.application.add_handler(CommandHandler("brainstorm", self.brainstorm_command))
        
        # Text message handler
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message)
        )
        
        # Voice message handler
        self.application.add_handler(
            MessageHandler(filters.VOICE, self.handle_voice_message)
        )
        
        # Photo handler
        self.application.add_handler(
            MessageHandler(filters.PHOTO, self.handle_photo_message)
        )
        
    async def initialize(self):
        """Initialize the Telegram application."""
        try:
            # Initialize and start the application - this properly initializes the HTTP client
            await self.application.initialize()
            await self.application.start()
            logger.info("Telegram handler initialized and started successfully")
        except Exception as e:
            logger.error(f"Error initializing Telegram handler: {e}")
            raise
    
    async def shutdown(self):
        """Shutdown the Telegram application."""
        try:
            await self.application.stop()
            await self.application.shutdown()
            logger.info("Telegram handler shutdown successfully")
        except Exception as e:
            logger.error(f"Error shutting down Telegram handler: {e}")
    
    async def get_or_create_user(self, db: AsyncSession, telegram_user) -> User:
        """Get or create user from Telegram user object."""
        stmt = select(User).where(User.telegram_id == telegram_user.id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                telegram_id=telegram_user.id,
                telegram_username=telegram_user.username,
                first_name=telegram_user.first_name,
                last_name=telegram_user.last_name,
                last_active_at=datetime.utcnow()
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)
        else:
            user.last_active_at = datetime.utcnow()
            await db.commit()
        
        return user
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = """👋 Welcome to Daystrom!

I'm your AI-powered personal memory and task assistant. Here's what I can do:

📝 **Capture anything**: Just send me your thoughts, tasks, or ideas as text, voice notes, or photos
🔍 **Smart search**: Use `/search <query>` to find related notes
📊 **Daily digests**: Get summaries of your tasks and ideas
💡 **Brainstorm**: Use `/brainstorm <topic>` to surface related ideas and connections

Just start sending me messages, and I'll organize everything for you!

Commands:
/help - Show this help message
/search <query> - Search your notes
/digest - Get a summary of recent items
/brainstorm <topic> - Brainstorm on a topic"""
        
        try:
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
            await update.message.reply_text(welcome_message)
        except Exception as e:
            logger.error(f"Error handling start command: {e}")
            try:
                await update.message.reply_text("Welcome to Daystrom! I'm ready to help you capture and organize your thoughts.")
            except:
                # If we can't send a message, just log the error
                logger.error("Failed to send welcome message")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """🤖 **Daystrom Commands:**

📝 **Text Messages**: Send me any text and I'll capture it for you
🎙️ **Voice Notes**: Send voice messages for transcription and capture
📷 **Photos**: Send photos with text for OCR and capture

**Commands:**
• `/start` - Welcome message and setup
• `/help` - Show this help message
• `/search <query>` - Search through your captured items
• `/digest` - Get a summary of recent items and upcoming tasks
• `/brainstorm <topic>` - Get related ideas and connections

**Examples:**
• "Remember to call mom tomorrow"
• "/search meeting notes"
• "/digest"
• "/brainstorm project ideas"

I'll automatically organize everything by type, extract dates and people, and make it all searchable!"""
        
        try:
            await update.message.reply_text(help_message)
        except Exception as e:
            logger.error(f"Error handling help command: {e}")
            try:
                await update.message.reply_text("I can help you capture and search your thoughts. Send me messages or use /search to find items!")
            except:
                logger.error("Failed to send help message")
    
    # Continue with remaining methods...
    # For brevity, I'll add the remaining methods in the same pattern
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        try:
            from app.database import AsyncSessionLocal
            
            query = " ".join(context.args) if context.args else ""
            if not query:
                await update.message.reply_text("Please provide a search query. Example: `/search meeting notes`")
                return
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Perform semantic search
                results = await memory_service.semantic_search(
                    db, user.id, query, limit=5
                )
                
                if not results:
                    await update.message.reply_text(f"No results found for '{query}'")
                    return
                
                response = f"🔍 **Search results for '{query}':**\n\n"
                for i, (item, score) in enumerate(results, 1):
                    # Truncate long content
                    content = item.content[:100] + "..." if len(item.content) > 100 else item.content
                    response += f"{i}. {content}\n"
                    if item.due_date:
                        response += f"   📅 Due: {item.due_date.strftime('%Y-%m-%d')}\n"
                    response += "\n"
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling search command: {e}")
            try:
                await update.message.reply_text("Sorry, I encountered an error during search.")
            except:
                logger.error("Failed to send search error message")
    
    async def digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /digest command."""
        try:
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Get recent items
                items = await memory_service.get_recent_items(
                    db, user.id, days=7, completed=False
                )
                
                if not items:
                    await update.message.reply_text("You don't have any recent items.")
                    return
                
                # Get upcoming calendar events
                calendar_events = await calendar_service.get_upcoming_events(
                    db, user.id, hours=48
                )
                
                # Generate digest using AI
                response = await openai_service.generate_digest(
                    [{"content": item.content, "type": str(item.item_type)} for item in items], [{"title": event.title, "start": event.start_time.isoformat()} for event in calendar_events] if calendar_events else []
                )
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling digest command: {e}")
            try:
                await update.message.reply_text("Sorry, I couldn't generate your digest.")
            except:
                logger.error("Failed to send digest error message")
    
    async def brainstorm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /brainstorm command."""
        try:
            from app.database import AsyncSessionLocal
            
            topic = " ".join(context.args) if context.args else ""
            if not topic:
                await update.message.reply_text("Please provide a brainstorming topic. Example: `/brainstorm productivity tools`")
                return
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Get related items
                related_items = await memory_service.semantic_search(
                    db, user.id, topic, limit=10
                )
                
                # Generate brainstorming response
                response = await openai_service.brainstorm(
                    topic, [{"content": item.content, "type": str(item.item_type)} for item, _ in related_items]
                )
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling brainstorm command: {e}")
            try:
                await update.message.reply_text("Sorry, I couldn't help with brainstorming.")
            except:
                logger.error("Failed to send brainstorm error message")
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages."""
        try:
            from app.database import AsyncSessionLocal
            
            text = update.message.text
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Store the message
                # Need to create ItemCreate object first
                from app.schemas.item import ItemCreate
                item_data = ItemCreate(content=text, media_type="text")
                await memory_service.create_item(
                    db, user.id, item_data
                )
                
                # Generate response
                # For now, just provide a simple acknowledgment
                response = "✅ Got it! I've saved that for you."
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            try:
                await update.message.reply_text("Sorry, I encountered an error processing your message.")
            except:
                logger.error("Failed to send text message error")
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages."""
        try:
            await update.message.reply_text("Voice message processing is not yet implemented.")
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
    
    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages."""
        try:
            await update.message.reply_text("Photo processing is not yet implemented.")
        except Exception as e:
            logger.error(f"Error handling photo message: {e}")
    
    async def process_webhook(self, update_data: dict):
        """Process webhook update from Telegram."""
        try:
            update = Update.de_json(update_data, self.bot)
            await self.application.process_update(update)
        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            raise


# Global instance
telegram_handler = TelegramHandler()

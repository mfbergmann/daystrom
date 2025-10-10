"""Telegram bot webhook handler and message processing."""
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import tempfile
import os
from typing import Optional
from datetime import datetime

from app.models import User, Item
from app.schemas.item import ItemCreate
from app.services.openai_service import openai_service
from app.services.memory_service import memory_service
from app.services.calendar_service import calendar_service
from config import settings
from loguru import logger


class TelegramHandler:
    """Handler for Telegram bot interactions."""
    
    def __init__(self):
        """Initialize Telegram bot."""
        self.bot = Bot(token=settings.telegram_bot_token)
        self.application = Application.builder().token(settings.telegram_bot_token).build()
        
        # Register handlers
        self._register_handlers()
    
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
        
        await update.message.reply_text(welcome_message)
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_message = """🤖 **Daystrom Commands**

📝 **Capturing Information**
Just send me any message:
- Text messages
- Voice notes (automatically transcribed)
- Photos (text extracted)

🔍 **Search**
`/search <query>` - Find related notes using natural language

📊 **Digest**
`/digest` - Get a summary of recent tasks and ideas

💡 **Brainstorm**
`/brainstorm <topic>` - Surface related ideas and connections

I automatically understand:
- Task types (ideas, tasks, events, references)
- Due dates and deadlines
- Priority levels
- Tags and people mentioned

Your information is organized intelligently and searchable semantically."""
        
        await update.message.reply_text(help_message)
    
    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages."""
        try:
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                content = update.message.text
                
                # Use OpenAI to classify and extract information
                extracted_info = await openai_service.classify_and_extract(content)
                
                # Create item
                item_data = ItemCreate(
                    content=content,
                    item_type=extracted_info.get('item_type'),
                    priority=extracted_info.get('priority'),
                    tags=extracted_info.get('tags', []),
                    counterparties=extracted_info.get('counterparties', []),
                    media_type='text'
                )
                
                # Parse due date if provided
                if extracted_info.get('due_date'):
                    try:
                        from dateutil import parser
                        item_data.due_date = parser.parse(extracted_info['due_date'])
                    except:
                        pass
                
                item = await memory_service.create_item(db, user.id, item_data)
                
                # Prepare response
                response = f"✅ Captured as **{item.item_type or 'note'}**"
                if item.tags:
                    response += f"\n🏷️ Tags: {', '.join(item.tags)}"
                if item.due_date:
                    response += f"\n📅 Due: {item.due_date.strftime('%Y-%m-%d')}"
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling text message: {e}")
            await update.message.reply_text("Sorry, I encountered an error processing your message.")
    
    async def handle_voice_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle voice messages."""
        try:
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Download voice file
                voice = update.message.voice
                file = await voice.get_file()
                
                with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as temp_file:
                    temp_path = temp_file.name
                    await file.download_to_drive(temp_path)
                
                try:
                    # Transcribe audio
                    transcription = await openai_service.transcribe_audio(temp_path)
                    
                    # Extract information
                    extracted_info = await openai_service.classify_and_extract(transcription)
                    
                    # Create item
                    item_data = ItemCreate(
                        content=transcription,
                        original_content=f"Voice message (duration: {voice.duration}s)",
                        item_type=extracted_info.get('item_type'),
                        priority=extracted_info.get('priority'),
                        tags=extracted_info.get('tags', []),
                        counterparties=extracted_info.get('counterparties', []),
                        media_type='voice',
                        media_file_id=voice.file_id
                    )
                    
                    if extracted_info.get('due_date'):
                        try:
                            from dateutil import parser
                            item_data.due_date = parser.parse(extracted_info['due_date'])
                        except:
                            pass
                    
                    item = await memory_service.create_item(db, user.id, item_data)
                    
                    response = f"🎤 Transcribed and captured as **{item.item_type or 'note'}**\n\n"
                    response += f"_{transcription}_"
                    if item.tags:
                        response += f"\n\n🏷️ Tags: {', '.join(item.tags)}"
                    
                    await update.message.reply_text(response)
                    
                finally:
                    # Clean up temp file
                    os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error handling voice message: {e}")
            await update.message.reply_text("Sorry, I couldn't transcribe your voice message.")
    
    async def handle_photo_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle photo messages."""
        try:
            from app.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Get highest quality photo
                photo = update.message.photo[-1]
                file = await photo.get_file()
                
                # Get file URL
                file_url = file.file_path
                
                # Get caption if provided
                caption = update.message.caption or ""
                
                # Analyze image
                prompt = "Extract any text from this image and describe its content. "
                if caption:
                    prompt += f"The user added this caption: {caption}"
                
                analysis = await openai_service.analyze_image(file_url, prompt)
                
                # Combine caption and analysis
                content = analysis
                if caption:
                    content = f"{caption}\n\n{analysis}"
                
                # Extract information
                extracted_info = await openai_service.classify_and_extract(content)
                
                # Create item
                item_data = ItemCreate(
                    content=content,
                    original_content=caption if caption else "Photo",
                    item_type=extracted_info.get('item_type'),
                    priority=extracted_info.get('priority'),
                    tags=extracted_info.get('tags', []),
                    counterparties=extracted_info.get('counterparties', []),
                    media_type='photo',
                    media_file_id=photo.file_id
                )
                
                if extracted_info.get('due_date'):
                    try:
                        from dateutil import parser
                        item_data.due_date = parser.parse(extracted_info['due_date'])
                    except:
                        pass
                
                item = await memory_service.create_item(db, user.id, item_data)
                
                response = f"📸 Photo analyzed and captured as **{item.item_type or 'note'}**"
                if item.tags:
                    response += f"\n🏷️ Tags: {', '.join(item.tags)}"
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling photo message: {e}")
            await update.message.reply_text("Sorry, I couldn't analyze your photo.")
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /search command."""
        try:
            from app.database import AsyncSessionLocal
            
            query = ' '.join(context.args)
            if not query:
                await update.message.reply_text("Please provide a search query. Example: `/search meeting notes`")
                return
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Perform semantic search
                results = await memory_service.semantic_search(
                    db, user.id, query, limit=5, threshold=0.6
                )
                
                if not results:
                    await update.message.reply_text("No matching items found.")
                    return
                
                response = f"🔍 **Search results for:** _{query}_\n\n"
                for i, result in enumerate(results, 1):
                    content = result['content']
                    if len(content) > 100:
                        content = content[:100] + "..."
                    
                    response += f"{i}. **{result['item_type'] or 'note'}** "
                    response += f"(similarity: {result['similarity']:.0%})\n"
                    response += f"   _{content}_\n"
                    if result['tags']:
                        response += f"   🏷️ {', '.join(result['tags'])}\n"
                    response += "\n"
                
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling search command: {e}")
            await update.message.reply_text("Sorry, I encountered an error during search.")
    
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
                
                # Prepare data for digest
                items_data = [
                    {
                        'content': item.content,
                        'item_type': item.item_type,
                        'due_date': item.due_date.isoformat() if item.due_date else None,
                        'tags': item.tags or []
                    }
                    for item in items[:20]
                ]
                
                events_data = [
                    {
                        'title': event.title,
                        'start_time': event.start_time.isoformat()
                    }
                    for event in calendar_events
                ]
                
                # Generate digest
                digest = await openai_service.generate_digest(items_data, events_data)
                
                response = f"📊 **Your Digest**\n\n{digest}"
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling digest command: {e}")
            await update.message.reply_text("Sorry, I couldn't generate your digest.")
    
    async def brainstorm_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /brainstorm command."""
        try:
            from app.database import AsyncSessionLocal
            
            topic = ' '.join(context.args)
            if not topic:
                await update.message.reply_text("Please provide a topic. Example: `/brainstorm project ideas`")
                return
            
            async with AsyncSessionLocal() as db:
                user = await self.get_or_create_user(db, update.effective_user)
                
                # Find related items
                related_items = await memory_service.semantic_search(
                    db, user.id, topic, limit=10, threshold=0.5
                )
                
                # Generate brainstorming response
                brainstorm = await openai_service.brainstorm(topic, related_items)
                
                response = f"💡 **Brainstorming:** _{topic}_\n\n{brainstorm}"
                await update.message.reply_text(response)
                
        except Exception as e:
            logger.error(f"Error handling brainstorm command: {e}")
            await update.message.reply_text("Sorry, I couldn't help with brainstorming.")
    
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


"""OpenAI API service for embeddings and completions."""
from typing import List, Dict, Any, Optional
from openai import AsyncOpenAI
from config import settings
from loguru import logger
import json


class OpenAIService:
    """Service for interacting with OpenAI API."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.reasoning_model = settings.openai_reasoning_model
        self.embedding_model = settings.openai_embedding_model
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for given text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise
    
    async def classify_and_extract(self, content: str) -> Dict[str, Any]:
        """
        Classify item and extract structured information.
        
        Args:
            content: The content to analyze
            
        Returns:
            Dictionary with extracted information
        """
        system_prompt = """You are an AI assistant that analyzes text and extracts structured information.
        
Given a piece of text, you should:
1. Classify it as one of: idea, task, event, reference, note
2. Extract any due dates or deadlines mentioned
3. Determine priority if indicated (low, medium, high)
4. Extract relevant tags or categories
5. Identify any people or organizations mentioned (counterparties)

Return the information in JSON format."""
        
        function_schema = {
            "name": "extract_item_info",
            "description": "Extract structured information from text",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_type": {
                        "type": "string",
                        "enum": ["idea", "task", "event", "reference", "note"],
                        "description": "The type of item"
                    },
                    "due_date": {
                        "type": "string",
                        "description": "ISO format date if a deadline is mentioned, null otherwise"
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Priority level if indicated"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Relevant tags or categories"
                    },
                    "counterparties": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "People or organizations mentioned"
                    }
                },
                "required": ["item_type"]
            }
        }
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
                functions=[function_schema],
                function_call={"name": "extract_item_info"}
            )
            
            function_call = response.choices[0].message.function_call
            if function_call:
                result = json.loads(function_call.arguments)
                return result
            
            return {"item_type": "note"}
            
        except Exception as e:
            logger.error(f"Error classifying content: {e}")
            return {"item_type": "note"}
    
    async def transcribe_audio(self, audio_file_path: str) -> str:
        """
        Transcribe audio file using Whisper API.
        
        Args:
            audio_file_path: Path to audio file
            
        Returns:
            Transcribed text
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = await self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file
                )
            return response.text
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise
    
    async def analyze_image(self, image_url: str, prompt: str = "Extract any text and describe the content of this image.") -> str:
        """
        Analyze image using Vision API.
        
        Args:
            image_url: URL of the image
            prompt: Instruction for image analysis
            
        Returns:
            Extracted text and description
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=1000
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error analyzing image: {e}")
            raise
    
    async def generate_digest(self, items: List[Dict[str, Any]], calendar_events: List[Dict[str, Any]] = None) -> str:
        """
        Generate a natural language digest of items and events.
        
        Args:
            items: List of item dictionaries
            calendar_events: Optional list of calendar events
            
        Returns:
            Formatted digest text
        """
        system_prompt = """You are a helpful assistant that creates concise, friendly daily digests.
        
Given a list of tasks, ideas, and events, create a natural, conversational summary that:
1. Highlights important tasks and deadlines
2. Mentions upcoming events
3. Surfaces interesting ideas
4. Uses a warm, encouraging tone
5. Keeps it brief but informative"""
        
        items_text = "\n".join([
            f"- [{item.get('item_type', 'note')}] {item.get('content', '')}"
            + (f" (due: {item.get('due_date')})" if item.get('due_date') else "")
            for item in items
        ])
        
        events_text = ""
        if calendar_events:
            events_text = "\n\nUpcoming events:\n" + "\n".join([
                f"- {event.get('title', '')} at {event.get('start_time', '')}"
                for event in calendar_events
            ])
        
        user_content = f"Items:\n{items_text}{events_text}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=500
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating digest: {e}")
            raise
    
    async def brainstorm(self, query: str, related_items: List[Dict[str, Any]]) -> str:
        """
        Generate brainstorming suggestions based on query and related items.
        
        Args:
            query: The brainstorming topic
            related_items: Semantically similar items from memory
            
        Returns:
            Brainstorming response
        """
        system_prompt = """You are a creative brainstorming assistant.
        
Given a topic and related notes from the user's memory, help them:
1. Make connections between ideas
2. Surface relevant past thoughts
3. Suggest new angles or directions
4. Ask thought-provoking questions
5. Be creative and encouraging"""
        
        context = "\n".join([
            f"- {item.get('content', '')}"
            for item in related_items[:5]
        ])
        
        user_content = f"Topic: {query}\n\nRelated notes:\n{context}"
        
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_content}
                ],
                max_tokens=800
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating brainstorm: {e}")
            raise


# Global instance
openai_service = OpenAIService()


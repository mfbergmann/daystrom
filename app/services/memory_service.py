"""Memory service for storing and retrieving items with semantic search."""
from typing import List, Dict, Any, Optional
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Item, Embedding, Tag
from app.services.openai_service import openai_service
from app.schemas.item import ItemCreate
from loguru import logger
from datetime import datetime


class MemoryService:
    """Service for managing items and semantic search."""
    
    async def create_item(
        self,
        db: AsyncSession,
        user_id: int,
        item_data: ItemCreate
    ) -> Item:
        """
        Create a new item with embedding.
        
        Args:
            db: Database session
            user_id: User ID
            item_data: Item creation data
            
        Returns:
            Created item
        """
        # Create item
        item = Item(
            user_id=user_id,
            content=item_data.content,
            original_content=item_data.original_content,
            item_type=item_data.item_type,
            due_date=item_data.due_date,
            priority=item_data.priority,
            tags=item_data.tags,
            counterparties=item_data.counterparties,
            media_type=item_data.media_type,
            media_file_id=item_data.media_file_id,
            metadata=item_data.metadata
        )
        db.add(item)
        await db.flush()
        
        # Generate and store embedding
        try:
            embedding_vector = await openai_service.get_embedding(item.content)
            embedding = Embedding(
                item_id=item.id,
                embedding=embedding_vector
            )
            db.add(embedding)
            
            # Update tag usage
            for tag_name in item_data.tags:
                await self._update_or_create_tag(db, user_id, tag_name)
            
            await db.commit()
            await db.refresh(item)
            
        except Exception as e:
            logger.error(f"Error creating item embedding: {e}")
            await db.rollback()
            raise
        
        return item
    
    async def semantic_search(
        self,
        db: AsyncSession,
        user_id: int,
        query: str,
        limit: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search across user's items.
        
        Args:
            db: Database session
            user_id: User ID
            query: Search query
            limit: Maximum number of results
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of matching items with similarity scores
        """
        try:
            # Generate query embedding
            query_embedding = await openai_service.get_embedding(query)
            
            # Perform vector similarity search
            # Using pgvector's <=> operator for cosine distance
            stmt = select(
                Item,
                (1 - Embedding.embedding.cosine_distance(query_embedding)).label('similarity')
            ).join(
                Embedding, Item.id == Embedding.item_id
            ).where(
                and_(
                    Item.user_id == user_id,
                    (1 - Embedding.embedding.cosine_distance(query_embedding)) >= threshold
                )
            ).order_by(
                (1 - Embedding.embedding.cosine_distance(query_embedding)).desc()
            ).limit(limit)
            
            result = await db.execute(stmt)
            rows = result.all()
            
            return [
                {
                    "item_id": row.Item.id,
                    "content": row.Item.content,
                    "item_type": row.Item.item_type,
                    "similarity": float(row.similarity),
                    "created_at": row.Item.created_at,
                    "tags": row.Item.tags or [],
                    "due_date": row.Item.due_date
                }
                for row in rows
            ]
            
        except Exception as e:
            logger.error(f"Error performing semantic search: {e}")
            raise
    
    async def get_recent_items(
        self,
        db: AsyncSession,
        user_id: int,
        days: int = 7,
        item_types: Optional[List[str]] = None,
        completed: bool = False
    ) -> List[Item]:
        """
        Get recent items for a user.
        
        Args:
            db: Database session
            user_id: User ID
            days: Number of days to look back
            item_types: Filter by item types
            completed: Include completed items
            
        Returns:
            List of items
        """
        stmt = select(Item).where(Item.user_id == user_id)
        
        if not completed:
            stmt = stmt.where(Item.completed == "pending")
        
        if item_types:
            stmt = stmt.where(Item.item_type.in_(item_types))
        
        stmt = stmt.order_by(Item.created_at.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def get_items_by_tag(
        self,
        db: AsyncSession,
        user_id: int,
        tag: str
    ) -> List[Item]:
        """
        Get items by tag.
        
        Args:
            db: Database session
            user_id: User ID
            tag: Tag name
            
        Returns:
            List of items with the tag
        """
        stmt = select(Item).where(
            and_(
                Item.user_id == user_id,
                Item.tags.contains([tag])
            )
        ).order_by(Item.created_at.desc())
        
        result = await db.execute(stmt)
        return result.scalars().all()
    
    async def _update_or_create_tag(
        self,
        db: AsyncSession,
        user_id: int,
        tag_name: str,
        tag_type: str = "general"
    ):
        """Update or create tag usage statistics."""
        stmt = select(Tag).where(
            and_(
                Tag.user_id == user_id,
                Tag.name == tag_name
            )
        )
        result = await db.execute(stmt)
        tag = result.scalar_one_or_none()
        
        if tag:
            tag.usage_count += 1
            tag.last_used_at = datetime.utcnow()
        else:
            tag = Tag(
                user_id=user_id,
                name=tag_name,
                tag_type=tag_type
            )
            db.add(tag)
    
    async def get_popular_tags(
        self,
        db: AsyncSession,
        user_id: int,
        limit: int = 20
    ) -> List[Tag]:
        """Get most frequently used tags."""
        stmt = select(Tag).where(
            Tag.user_id == user_id
        ).order_by(Tag.usage_count.desc()).limit(limit)
        
        result = await db.execute(stmt)
        return result.scalars().all()


# Global instance
memory_service = MemoryService()


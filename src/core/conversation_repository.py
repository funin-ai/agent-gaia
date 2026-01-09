"""Conversation and message repository for database operations."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from src.core.database import get_db_pool
from src.utils.logger import logger


@dataclass
class Message:
    """Message data model."""

    id: Optional[int] = None
    conversation_id: str = ""
    role: str = ""  # 'user', 'assistant', 'system'
    content: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cost: Optional[float] = None
    created_at: Optional[datetime] = None


@dataclass
class Conversation:
    """Conversation data model."""

    id: str = ""
    user_id: Optional[str] = None
    title: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    messages: list[Message] = None

    def __post_init__(self):
        if self.messages is None:
            self.messages = []


class ConversationRepository:
    """Repository for conversation and message database operations."""

    @staticmethod
    def generate_id() -> str:
        """Generate a new conversation ID."""
        return str(uuid.uuid4())

    @staticmethod
    async def create_conversation(
        user_id: Optional[str] = None, title: Optional[str] = None
    ) -> Optional[Conversation]:
        """Create a new conversation.
        Args:
            user_id: Optional user ID (UUID string)
            title: Optional conversation title
        Returns:
            Created conversation or None on failure
        """
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                conversation_id = ConversationRepository.generate_id()

                await conn.execute(
                    """
                    INSERT INTO conversations (id, user_id, title)
                    VALUES ($1, $2, $3)
                    """,
                    conversation_id,
                    uuid.UUID(user_id) if user_id else None,
                    title,
                )

                logger.info(f"Created conversation: {conversation_id}")
                return Conversation(
                    id=conversation_id,
                    user_id=user_id,
                    title=title,
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None

    @staticmethod
    async def add_message(
        conversation_id: str,
        role: str,
        content: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        input_tokens: Optional[int] = None,
        output_tokens: Optional[int] = None,
        cost: Optional[float] = None,
    ) -> Optional[Message]:
        """Add a message to a conversation.
        Args:
            conversation_id: Conversation ID
            role: Message role ('user', 'assistant', 'system')
            content: Message content
            provider: LLM provider name
            model: Model name
            input_tokens: Input token count
            output_tokens: Output token count
            cost: Cost in USD

        Returns:
            Created message or None on failure
        """
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                row = await conn.fetchrow(
                    """
                    INSERT INTO messages
                    (conversation_id, role, content, provider, model, input_tokens, output_tokens, cost)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id, created_at
                    """,
                    conversation_id,
                    role,
                    content,
                    provider,
                    model,
                    input_tokens,
                    output_tokens,
                    cost,
                )

                # Update conversation's updated_at
                await conn.execute(
                    """
                    UPDATE conversations SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    conversation_id,
                )

                logger.debug(f"Added message to conversation {conversation_id[:8]}...")
                return Message(
                    id=row["id"],
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    provider=provider,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost=cost,
                    created_at=row["created_at"],
                )
        except Exception as e:
            logger.error(f"Failed to add message: {e}")
            return None

    @staticmethod
    async def get_conversation(conversation_id: str) -> Optional[Conversation]:
        """Get a conversation with all its messages.
        Args:
            conversation_id: Conversation ID
        Returns:
            Conversation with messages or None
        """
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                # Get conversation
                conv_row = await conn.fetchrow(
                    """
                    SELECT id, user_id, title, created_at, updated_at
                    FROM conversations WHERE id = $1
                    """,
                    conversation_id,
                )

                if not conv_row:
                    return None

                # Get messages
                msg_rows = await conn.fetch(
                    """
                    SELECT id, conversation_id, 
                           role, 
                           content, 
                           provider, 
                           model,
                           input_tokens, output_tokens, cost, created_at
                    FROM messages
                    WHERE conversation_id = $1
                    ORDER BY created_at ASC
                    """,
                    conversation_id,
                )

                messages = [
                    Message(
                        id=row["id"],
                        conversation_id=row["conversation_id"],
                        role=row["role"],
                        content=row["content"],
                        provider=row["provider"],
                        model=row["model"],
                        input_tokens=row["input_tokens"],
                        output_tokens=row["output_tokens"],
                        cost=float(row["cost"]) if row["cost"] else None,
                        created_at=row["created_at"],
                    )
                    for row in msg_rows
                ]

                return Conversation(
                    id=conv_row["id"],
                    user_id=str(conv_row["user_id"]) if conv_row["user_id"] else None,
                    title=conv_row["title"],
                    created_at=conv_row["created_at"],
                    updated_at=conv_row["updated_at"],
                    messages=messages,
                )
        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None

    @staticmethod
    async def list_conversations(
        user_id: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> list[Conversation]:
        """List conversations, optionally filtered by user.
        Args:
            user_id: Optional user ID to filter by
            limit: Maximum number of results
            offset: Offset for pagination
        Returns:
            List of conversations (without messages)
        """
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                if user_id:
                    rows = await conn.fetch(
                        """
                        SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                               (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as msg_count
                        FROM conversations c
                        WHERE c.user_id = $1
                        ORDER BY c.updated_at DESC
                        LIMIT $2 OFFSET $3
                        """,
                        uuid.UUID(user_id),
                        limit,
                        offset,
                    )
                else:
                    rows = await conn.fetch(
                        """
                        SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                               (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as msg_count
                        FROM conversations c
                        ORDER BY c.updated_at DESC
                        LIMIT $1 OFFSET $2
                        """,
                        limit,
                        offset,
                    )

                return [
                    Conversation(
                        id=row["id"],
                        user_id=str(row["user_id"]) if row["user_id"] else None,
                        title=row["title"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            return []

    @staticmethod
    async def update_title(conversation_id: str, title: str) -> bool:
        
        """Update conversation title.
        Args:
            conversation_id: Conversation ID
            title: New title
        Returns:
            True on success
        """
        
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    """
                    UPDATE conversations SET title = $1, updated_at = CURRENT_TIMESTAMP
                    WHERE id = $2
                    """,
                    title,
                    conversation_id,
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update title: {e}")
            return False

    @staticmethod
    async def delete_conversation(conversation_id: str) -> bool:
        """
        Delete a conversation and all its messages.
        Args:
            conversation_id: Conversation ID
        Returns:
            True on success
        """
        try:
            pool = get_db_pool()
            async with pool.connection() as conn:
                await conn.execute(
                    "DELETE FROM conversations WHERE id = $1", conversation_id
                )
                logger.info(f"Deleted conversation: {conversation_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to delete conversation: {e}")
            return False

    @staticmethod
    async def generate_title_from_content(content: str, max_length: int = 50) -> str:
        """Generate a title from message content.
        Args:
            content: Message content
            max_length: Maximum title length
        Returns:
            Generated title
        """
        
        # Take first line or first N characters
        title = content.split("\n")[0].strip()
        if len(title) > max_length:
            title = title[: max_length - 3] + "..."
        
        return title or "New Conversation"

"""Pydantic schemas for AgentGaia."""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class Provider(str, Enum):
    """LLM Provider enum."""
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"


class WebSocketMessageType(str, Enum):
    """WebSocket message types."""
    CHAT = "chat"
    STREAMING = "streaming"
    COMPLETE = "complete"
    ERROR = "error"
    RATING = "rating"
    CONNECTED = "connected"
    BACKUP_SWITCH = "backup_switch"


class ChatRequest(BaseModel):
    """Request for chat message."""
    type: str = "chat"
    message: str
    message_id: int = 0


class StreamingMessage(BaseModel):
    """Streaming response message."""
    provider: str
    status: str = "streaming"
    chunk: str


class CompleteMessage(BaseModel):
    """Completion message."""
    provider: str
    status: str = "complete"
    total_tokens: Optional[int] = None


class ErrorMessage(BaseModel):
    """Error message."""
    provider: str
    status: str = "error"
    error: str
    backup_provider: Optional[str] = None


class UserRating(BaseModel):
    """User rating for LLM response."""
    type: str = "rating"
    provider: str
    rating: int = Field(ge=1, le=5)
    message_id: int = 0


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str
    providers: dict[str, bool]

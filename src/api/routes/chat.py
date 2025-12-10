"""WebSocket chat API for multi-LLM streaming."""

import asyncio
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

from src.core.llm_router import get_llm_router
from src.core.settings import get_settings
from src.utils.logger import logger
from src.models.schemas import (
    StreamingMessage,
    CompleteMessage,
    ErrorMessage,
)
from src.utils.token_counter import get_token_counter
from src.api.routes.upload import uploaded_files


def is_ws_connected(websocket: WebSocket) -> bool:
    """Check if WebSocket is still connected."""
    return websocket.client_state == WebSocketState.CONNECTED


async def safe_send(websocket: WebSocket, data: dict) -> bool:
    """Safely send data to WebSocket, checking connection state first."""
    if not is_ws_connected(websocket):
        return False
    try:
        await websocket.send_json(data)
        return True
    except Exception:
        return False


router = APIRouter(prefix="/api/v1", tags=["chat"])

# User ratings store (message_id -> provider -> rating)
user_ratings: dict[int, dict[str, int]] = {}

# Shared conversation history (all providers share the same context)
conversation_history: list = []

# System prompt for all providers
SYSTEM_PROMPT = (
    "당신은 유능한 AI 어시스턴트입니다. 사용자의 질문에 친절하고 정확하게 답변해주세요."
)

# Max history messages to keep (to avoid token limits)
MAX_HISTORY_MESSAGES = 50


class ConnectionManager:
    """Manages WebSocket connections for multiple providers."""

    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, provider: str, websocket: WebSocket):
        """Accept and register a WebSocket connection.

        Args:
            provider: Provider name (claude, openai, gemini)
            websocket: WebSocket instance
        """
        await websocket.accept()
        async with self._lock:
            self.active_connections[provider] = websocket
        logger.info(f"WebSocket connected: {provider}")

    def disconnect(self, provider: str):
        """Remove a WebSocket connection.

        Args:
            provider: Provider name
        """
        if provider in self.active_connections:
            del self.active_connections[provider]
            logger.info(f"WebSocket disconnected: {provider}")

    async def send_to_provider(self, provider: str, message: dict):
        """Send message to a specific provider's WebSocket.

        Args:
            provider: Provider name
            message: Message dict to send
        """
        if provider in self.active_connections:
            try:
                await self.active_connections[provider].send_json(message)
            except Exception as e:
                logger.error(f"Failed to send to {provider}: {e}")

    async def broadcast(self, message: dict):
        """Broadcast message to all connected WebSockets.

        Args:
            message: Message dict to send
        """
        for provider, ws in list(self.active_connections.items()):
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {provider}: {e}")

    def get_connected_providers(self) -> list[str]:
        """Get list of connected provider names.

        Returns:
            List of provider names
        """
        return list(self.active_connections.keys())


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, provider: str):
    """WebSocket endpoint for streaming LLM responses.

    Args:
        websocket: WebSocket connection
        provider: LLM provider name (claude, openai, gemini)
    """
    await manager.connect(provider, websocket)

    # Send connection confirmation
    await websocket.send_json(
        {"type": "connected", "provider": provider, "status": "ready"}
    )

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                message = data.get("message", "")
                message_id = data.get("message_id", 0)
                # File attachments: list of filenames
                attachments = data.get("attachments", [])

                # Start chat in background task
                asyncio.create_task(
                    process_chat(provider, message, message_id, websocket, attachments)
                )

            elif data.get("type") == "rating":
                message_id = data.get("message_id", 0)
                rating = data.get("rating")
                if message_id not in user_ratings:
                    user_ratings[message_id] = {}
                user_ratings[message_id][provider] = rating
                logger.info(
                    f"Rating received: {provider} = {rating} stars (msg: {message_id})"
                )

            elif data.get("type") == "clear_history":
                conversation_history.clear()
                logger.info("Conversation history cleared")
                await safe_send(
                    websocket, {"type": "history_cleared", "provider": provider}
                )

    except WebSocketDisconnect:
        manager.disconnect(provider)
    except Exception as e:
        logger.error(f"WebSocket error for {provider}: {e}")
        manager.disconnect(provider)


def _build_message_content(
    message: str, attachments: list[str], provider: str
) -> tuple[str, list | None]:
    """Build message content with file attachments.

    Args:
        message: User text message
        attachments: List of filenames to attach
        provider: LLM provider name (for format compatibility)

    Returns:
        Tuple of (text_for_history, multimodal_content_or_none)
        - text_for_history: Plain text version for conversation history
        - multimodal_content: List content for current message if images present
    """
    if not attachments:
        return message, None

    text_context = []
    image_parts = []

    for filename in attachments:
        if filename not in uploaded_files:
            logger.warning(f"Attachment not found: {filename}")
            continue

        file_data = uploaded_files[filename]

        if file_data.has_image:
            # Add image for Vision API
            image_parts.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{file_data.mime_type};base64,{file_data.image_base64}"
                }
            })
            # Add text description for history
            text_context.append(f"[Image: {filename}]")
            logger.info(f"Added image attachment: {filename}")
        elif file_data.has_text:
            # Add text content as context
            text_context.append(f"[File: {filename}]\n{file_data.text_content}")
            logger.info(f"Added text attachment: {filename} ({len(file_data.text_content)} chars)")

    # Build plain text version for history
    if text_context:
        text_for_history = "\n\n".join(text_context) + f"\n\n---\n\n{message}"
    else:
        text_for_history = message

    # If we have images, return multimodal content for current message
    if image_parts:
        multimodal_content = [{"type": "text", "text": text_for_history}] + image_parts
        return text_for_history, multimodal_content

    return text_for_history, None


async def process_chat(
    provider: str,
    message: str,
    message_id: int,
    websocket: WebSocket,
    attachments: list[str] | None = None,
):
    """Process chat message using specified LLM provider.

    Args:
        provider: LLM provider name
        message: User message
        message_id: Message ID for tracking
        websocket: WebSocket for sending responses
        attachments: List of filenames to include as context
    """
    try:
        if not message.strip() and not attachments:
            await safe_send(
                websocket,
                ErrorMessage(provider=provider, error="Empty message").model_dump(),
            )
            return

        # Get LLM router
        llm_router = get_llm_router()

        # Build message content with file attachments
        text_for_history, multimodal_content = _build_message_content(
            message, attachments or [], provider
        )

        # Add plain text to shared history (compatible with all providers)
        conversation_history.append(HumanMessage(content=text_for_history))

        # Trim history if too long
        if len(conversation_history) > MAX_HISTORY_MESSAGES:
            del conversation_history[:-MAX_HISTORY_MESSAGES]

        # Build messages for current request
        # Use multimodal content for current message if available (images)
        if multimodal_content:
            # Replace last message with multimodal version for this request only
            history_except_last = conversation_history[:-1]
            current_message = HumanMessage(content=multimodal_content)
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + history_except_last + [current_message]
        else:
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + conversation_history

        # Stream response and collect full response
        actual_provider = provider
        full_response = ""

        try:
            async for chunk in llm_router.astream(provider, messages):
                if not is_ws_connected(websocket):
                    logger.info(f"WebSocket disconnected during streaming: {provider}")
                    return
                full_response += chunk
                await safe_send(
                    websocket,
                    StreamingMessage(
                        provider=actual_provider, chunk=chunk
                    ).model_dump(),
                )

        except Exception as e:
            if not is_ws_connected(websocket):
                return

            # Try backup provider
            logger.warning(f"{provider} failed, trying backup: {e}")
            backup_provider = llm_router._try_backup(provider)
            actual_provider = backup_provider.__class__.__name__.lower().replace(
                "chat", ""
            )

            await safe_send(
                websocket,
                {
                    "type": "backup_switch",
                    "original_provider": provider,
                    "backup_provider": actual_provider,
                    "reason": str(e),
                },
            )

            async for chunk in backup_provider.astream(messages):
                if not is_ws_connected(websocket):
                    return
                if hasattr(chunk, "content"):
                    content = chunk.content
                    if isinstance(content, str):
                        full_response += content
                    await safe_send(
                        websocket,
                        StreamingMessage(
                            provider=actual_provider,
                            chunk=content if isinstance(content, str) else str(content),
                        ).model_dump(),
                    )

        # Add assistant response to shared history
        if full_response:
            conversation_history.append(AIMessage(content=full_response))

            # Track token usage and cost
            settings = get_settings()
            model_name = settings.llm.models.get(actual_provider, "unknown")
            token_counter = get_token_counter()
            await token_counter.track_usage(
                provider=actual_provider,
                model=model_name,
                input_text=message,
                output_text=full_response,
                messages=messages,
            )

        # Send completion message
        await safe_send(
            websocket, CompleteMessage(provider=actual_provider).model_dump()
        )

    except Exception as e:
        logger.error(f"Chat failed for {provider}: {e}")
        await safe_send(
            websocket, ErrorMessage(provider=provider, error=str(e)).model_dump()
        )


@router.get("/providers")
async def get_providers():
    """Get available LLM providers and their status.

    Returns:
        Provider information
    """
    settings = get_settings()
    return {
        "providers": list(settings.llm.models.keys()),
        "models": settings.llm.models,
        "primary": settings.llm.primary_provider,
        "backup_chain": settings.llm.backup_chain,
        "connected": manager.get_connected_providers(),
    }


@router.get("/health")
async def health_check():
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "connected_providers": manager.get_connected_providers(),
    }

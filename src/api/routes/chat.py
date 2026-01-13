"""WebSocket chat API for multi-LLM streaming."""

import asyncio
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
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
from src.services.web_search import (
    get_web_search_service,
    detect_search_intent,
)
from src.services.rag_service import get_rag_service
from src.core.conversation_repository import ConversationRepository


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

# Current conversation ID (shared across providers)
current_conversation_id: Optional[str] = None

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

    # Generate unique session ID for this WebSocket connection
    session_id = f"{provider}_{id(websocket)}"
    token_counter = get_token_counter()

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
                    process_chat(provider, message, message_id, websocket, attachments, session_id)
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
                global current_conversation_id
                conversation_history.clear()
                current_conversation_id = None
                # Reset session usage statistics
                token_counter.reset_session(session_id)
                logger.info(f"Conversation history and session usage cleared: {session_id}")
                await safe_send(
                    websocket, {
                        "type": "history_cleared",
                        "provider": provider,
                        "session": token_counter.get_session(session_id).to_dict(),
                    }
                )

            elif data.get("type") == "load_conversation":
                # Load existing conversation from DB
                conv_id = data.get("conversation_id")
                if conv_id:
                    conv = await ConversationRepository.get_conversation(conv_id)
                    if conv:
                        conversation_history.clear()
                        current_conversation_id = conv_id
                        # Rebuild history from DB
                        for msg in conv.messages:
                            if msg.role == "user":
                                conversation_history.append(HumanMessage(content=msg.content))
                            elif msg.role == "assistant":
                                conversation_history.append(AIMessage(content=msg.content))
                        logger.info(f"Loaded conversation {conv_id} with {len(conv.messages)} messages")
                        await safe_send(
                            websocket, {
                                "type": "conversation_loaded",
                                "provider": provider,
                                "conversation_id": conv_id,
                                "title": conv.title,
                                "message_count": len(conv.messages),
                            }
                        )
                    else:
                        await safe_send(
                            websocket, {
                                "type": "error",
                                "provider": provider,
                                "error": f"Conversation {conv_id} not found",
                            }
                        )

    except WebSocketDisconnect:
        manager.disconnect(provider)
        # Clean up session on disconnect
        token_counter.remove_session(session_id)
    except Exception as e:
        logger.error(f"WebSocket error for {provider}: {e}")
        manager.disconnect(provider)
        token_counter.remove_session(session_id)


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
    session_id: str | None = None,
):
    """Process chat message using specified LLM provider.

    Args:
        provider: LLM provider name
        message: User message
        message_id: Message ID for tracking
        websocket: WebSocket for sending responses
        attachments: List of filenames to include as context
        session_id: Unique session identifier for usage tracking
    """
    global current_conversation_id

    try:
        if not message.strip() and not attachments:
            await safe_send(
                websocket,
                ErrorMessage(provider=provider, error="Empty message").model_dump(),
            )
            return

        # Get LLM router
        llm_router = get_llm_router()

        # Check for web search intent
        search_context = ""
        has_search_intent, search_query = detect_search_intent(message)

        if has_search_intent and search_query:
            # Notify client that search is in progress
            await safe_send(
                websocket,
                {
                    "type": "searching",
                    "provider": provider,
                    "query": search_query,
                }
            )

            # Perform web search
            web_search = get_web_search_service()
            search_response = await web_search.search(search_query)

            # Send search results to client
            await safe_send(
                websocket,
                {
                    "type": "search_results",
                    "provider": provider,
                    "query": search_query,
                    "results": [
                        {
                            "title": r.title,
                            "url": r.url,
                            "snippet": r.snippet,
                        }
                        for r in search_response.results
                    ],
                    "has_results": search_response.has_results,
                }
            )

            # Build search context for RAG
            if search_response.has_results:
                search_context = search_response.to_context()
                logger.info(f"Web search context added: {len(search_context)} chars")

        # RAG search for relevant documents
        rag_context = ""
        settings = get_settings()
        if settings.rag.enabled:
            try:
                # Notify client that RAG search is in progress
                await safe_send(
                    websocket,
                    {
                        "type": "rag_searching",
                        "provider": provider,
                        "collection": settings.rag.collection_name,
                    }
                )

                # Perform RAG search
                rag_service = get_rag_service()
                rag_response = await rag_service.search(message)

                if rag_response.success and rag_response.results:
                    # Send RAG results to client
                    await safe_send(
                        websocket,
                        {
                            "type": "rag_results",
                            "provider": provider,
                            "collection": rag_response.collection,
                            "results_count": len(rag_response.results),
                            "processing_time_ms": rag_response.processing_time_ms,
                        }
                    )

                    # Build RAG context for LLM
                    rag_context = rag_service.format_context(rag_response.results)
                    logger.info(f"RAG context added: {len(rag_context)} chars, {len(rag_response.results)} docs")
                else:
                    if rag_response.error:
                        logger.warning(f"RAG search failed: {rag_response.error}")
                    else:
                        logger.info("RAG search returned no results")

            except Exception as e:
                logger.error(f"RAG search error: {e}")
                # Continue without RAG context on error

        # Build message content with file attachments
        text_for_history, multimodal_content = _build_message_content(
            message, attachments or [], provider
        )

        # Prepend RAG context if available (internal knowledge)
        if rag_context:
            text_for_history = f"{rag_context}\n\n---\n\n{text_for_history}"
            if multimodal_content:
                multimodal_content[0]["text"] = text_for_history

        # Prepend web search context if available (external knowledge)
        if search_context:
            text_for_history = f"{search_context}\n\n---\n\n사용자 질문: {text_for_history}"
            if multimodal_content:
                # Update the text part of multimodal content
                multimodal_content[0]["text"] = text_for_history

        # Add plain text to shared history (compatible with all providers)
        conversation_history.append(HumanMessage(content=text_for_history))

        # Trim history if too long
        if len(conversation_history) > MAX_HISTORY_MESSAGES:
            del conversation_history[:-MAX_HISTORY_MESSAGES]

        # Create new conversation if none exists
        if current_conversation_id is None:
            title = await ConversationRepository.generate_title_from_content(message)
            conv = await ConversationRepository.create_conversation(title=title)
            if conv:
                current_conversation_id = conv.id
                logger.info(f"Created new conversation: {current_conversation_id}")
                await safe_send(
                    websocket, {
                        "type": "conversation_created",
                        "provider": provider,
                        "conversation_id": current_conversation_id,
                        "title": title,
                    }
                )

        # Save user message to DB
        if current_conversation_id:
            await ConversationRepository.add_message(
                conversation_id=current_conversation_id,
                role="user",
                content=text_for_history
            )

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

            # Use session_id for per-session tracking
            effective_session_id = session_id or f"{provider}_unknown"
            usage = await token_counter.track_usage(
                session_id=effective_session_id,
                provider=actual_provider,
                model=model_name,
                input_text=message,
                output_text=full_response,
                messages=messages,
            )

            # Save assistant message to DB with usage info
            if current_conversation_id:
                await ConversationRepository.add_message(
                    conversation_id=current_conversation_id,
                    role="assistant",
                    content=full_response,
                    provider=actual_provider,
                    model=model_name,
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cost=usage.total_cost
                )

            # Send usage statistics to client
            await safe_send(
                websocket,
                {
                    "type": "usage",
                    "provider": actual_provider,
                    "model": model_name,
                    "message": {
                        "input_tokens": usage.input_tokens,
                        "output_tokens": usage.output_tokens,
                        "total_tokens": usage.total_tokens,
                        "cost": round(usage.total_cost, 6),
                    },
                    "session": token_counter.get_session(effective_session_id).to_dict(),
                    "conversation_id": current_conversation_id,
                },
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


@router.get("/export")
async def export_conversation(format: str = "markdown"):
    """Export conversation history as Markdown or text.

    Args:
        format: Export format (markdown, text)

    Returns:
        Conversation as downloadable file
    """
    if not conversation_history:
        return {"error": "No conversation to export", "success": False}

    # Build markdown content
    lines = []
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if format == "markdown":
        lines.append("# AgentGaia Conversation Export")
        lines.append(f"\n**Exported:** {timestamp}\n")
        lines.append("---\n")

        for msg in conversation_history:
            if isinstance(msg, HumanMessage):
                lines.append("## User\n")
                lines.append(f"{msg.content}\n")
            elif isinstance(msg, AIMessage):
                lines.append("## Assistant\n")
                lines.append(f"{msg.content}\n")
            lines.append("")  # Empty line between messages

        content = "\n".join(lines)
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        media_type = "text/markdown"
    else:
        # Plain text format
        lines.append(f"AgentGaia Conversation Export - {timestamp}")
        lines.append("=" * 50)
        lines.append("")

        for msg in conversation_history:
            if isinstance(msg, HumanMessage):
                lines.append("[User]")
                lines.append(msg.content)
            elif isinstance(msg, AIMessage):
                lines.append("[Assistant]")
                lines.append(msg.content)
            lines.append("-" * 30)

        content = "\n".join(lines)
        filename = f"conversation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        media_type = "text/plain"

    return Response(
        content=content,
        media_type=media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@router.get("/conversations")
async def list_conversations(limit: int = 50, offset: int = 0):
    """List all conversations.

    Args:
        limit: Maximum number of results
        offset: Offset for pagination

    Returns:
        List of conversations
    """
    conversations = await ConversationRepository.list_conversations(
        limit=limit, offset=offset
    )
    return {
        "conversations": [
            {
                "id": c.id,
                "title": c.title,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in conversations
        ],
        "current_conversation_id": current_conversation_id,
    }


@router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """Get a conversation with all its messages.

    Args:
        conversation_id: Conversation ID

    Returns:
        Conversation with messages
    """
    conv = await ConversationRepository.get_conversation(conversation_id)
    if not conv:
        return {"error": "Conversation not found", "success": False}

    return {
        "id": conv.id,
        "title": conv.title,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "provider": m.provider,
                "model": m.model,
                "input_tokens": m.input_tokens,
                "output_tokens": m.output_tokens,
                "cost": float(m.cost) if m.cost else None,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in conv.messages
        ],
    }


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Delete a conversation.

    Args:
        conversation_id: Conversation ID

    Returns:
        Success status
    """
    global current_conversation_id

    success = await ConversationRepository.delete_conversation(conversation_id)
    if not success:
        return {"error": "Failed to delete conversation", "success": False}

    # If deleting current conversation, clear history
    if current_conversation_id == conversation_id:
        conversation_history.clear()
        current_conversation_id = None

    return {"success": True, "message": f"Conversation {conversation_id} deleted"}


@router.patch("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, title: str):
    """Update conversation title.

    Args:
        conversation_id: Conversation ID
        title: New title

    Returns:
        Success status
    """
    success = await ConversationRepository.update_title(conversation_id, title)
    if not success:
        return {"error": "Failed to update title", "success": False}

    return {"success": True, "title": title}

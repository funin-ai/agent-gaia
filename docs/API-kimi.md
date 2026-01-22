# AgentGaia API Documentation (KIMI Revision)

**Base URL**: `http://localhost:9033`  
**Version**: 0.1.0  
**Last Updated**: 2025-01-21  
**Status**: Production-Ready (Based on Actual Implementation)

---

## ⚡ Quick Start for UI Development

```javascript
// WebSocket Client Example
const ws = new WebSocket('ws://localhost:9033/api/v1/ws/chat?provider=claude');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  
  // Real-world message structure (IMPORTANT)
  if (msg.type === 'streaming' || msg.status === 'streaming') {
    console.log('Chunk:', msg.chunk);
  }
  if (msg.type === 'complete' || msg.status === 'complete') {
    console.log('Response finished');
  }
  if (msg.type === 'error' || msg.status === 'error') {
    console.error('Error:', msg.error);
  }
};
```

---

## Table of Contents

1. [WebSocket API](#websocket-api) - 실시간 채팅 (핵심)
2. [Chat REST API](#chat-rest-api) - 대화 관리
3. [Upload API](#upload-api) - 파일 업로드
4. [Auth API](#auth-api) - OAuth 인증

---

## WebSocket API

### Real-World Connection

```
ws://localhost:9033/api/v1/ws/chat?provider={provider}
```

**Supported Providers**: `claude`, `openai`, `gemini`

**Important**: Connect to **multiple WebSockets simultaneously** (one per provider) for multi-LLM streaming.

---

### Client → Server Messages

#### 1. Chat Message (채팅 전송)

```json
{
  "type": "chat",
  "message": "사용자 메시지",
  "message_id": 1,
  "attachments": ["document.pdf"]
}
```

**IMPORTANT**: `attachments` must be **pre-uploaded** via `/api/v1/upload` endpoint first.

#### 2. Rating (응답 평가)

```json
{
  "type": "rating",
  "message_id": 1,
  "rating": 5
}
```

**Rating Scale**: 1-5 stars

#### 3. Clear History (대화 초기화)

```json
{
  "type": "clear_history"
}
```

**Effect**: Clears shared conversation history across ALL providers.

#### 4. Load Conversation (대화 불러오기)

```json
{
  "type": "load_conversation",
  "conversation_id": "uuid-string"
}
```

---

### Server → Client Messages (REAL-WORLD)

#### ⚠️ **IMPORTANT: Field Structure**

Messages use **either** `type` **or** `status` field (legacy support). **Check both** for production stability:

```javascript
// Production-safe handling
const msgType = msg.type || msg.status;
```

#### 1. Connected (연결 확인)

```json
{
  "type": "connected",
  "provider": "claude",
  "status": "ready"
}
```

#### 2. Streaming (스트리밍 응답 - Main Response)

```json
{
  "provider": "claude",
  "status": "streaming",
  "chunk": "안녕하세요! "
}
```

**Key Points**:
- **Multiple chunks** sent sequentially
- **Aggregate chunks** to build full response
- **Provider-specific** (each WS connection streams independently)
- **Type**: Real-time AI response

#### 3. Complete (응답 완료)

```json
{
  "provider": "claude",
  "status": "complete"
}
```

**Action**: Clear buffer, ready for next message.

#### 4. Error (에러 발생)

```json
{
  "provider": "claude",
  "status": "error",
  "error": "Rate limit exceeded"
}
```

**Note**: System **auto-switches to backup provider** on error.

#### 5. Backup Switch (프로바이더 자동 전환)

```json
{
  "type": "backup_switch",
  "original_provider": "claude",
  "backup_provider": "openai",
  "reason": "Rate limit exceeded"
}
```

**Important**: Backup chain is defined in config:
```yaml
llm:
  backup_chain: ["claude", "openai", "gemini"]
```

#### 6. Searching (웹 검색 시작)

```json
{
  "type": "searching",
  "provider": "claude",
  "query": "2025년 인공지능 트렌드"
}
```

**Trigger**: Auto-detected when user says "웹 검색해줘" or "search for..."

#### 7. Search Results (웹 검색 결과)

```json
{
  "type": "search_results",
  "provider": "claude",
  "query": "2025년 인공지능 트렌드",
  "results": [
    {
      "title": "AI Trends 2025",
      "url": "https://example.com",
      "snippet": "AI will revolutionize..."
    }
  ],
  "has_results": true
}
```

#### 8. RAG Searching (낙방지식 검색)

```json
{
  "type": "rag_searching",
  "provider": "claude",
  "collection": "homepage_collection"
}
```

**Purpose**: Searches internal knowledge base for context.

#### 9. RAG Results (낙방지식 검색 결과)

```json
{
  "type": "rag_results",
  "provider": "claude",
  "collection": "homepage_collection",
  "results_count": 5,
  "processing_time_ms": 123.45
}
```

#### 10. Usage (실시간 토큰 사용량)

```json
{
  "type": "usage",
  "provider": "claude",
  "model": "claude-opus-4-5-20251101",
  "message": {
    "input_tokens": 150,
    "output_tokens": 200,
    "total_tokens": 350,
    "cost": 0.02625
  },
  "session": {
    "total_input_tokens": 500,
    "total_output_tokens": 800,
    "total_tokens": 1300,
    "total_cost": 0.0975,
    "request_count": 3
  },
  "conversation_id": "uuid-string"
}
```

**Critical**: Real-time cost tracking for budget control.

#### 11. Conversation Created (새 대화 생성)

```json
{
  "type": "conversation_created",
  "provider": "claude",
  "conversation_id": "uuid-string",
  "title": "AI 기술 질의"
}
```

**Trigger**: First message in a session automatically creates conversation.

#### 12. Conversation Loaded (대화 불러옴)

```json
{
  "type": "conversation_loaded",
  "provider": "claude",
  "conversation_id": "uuid-string",
  "title": "AI 기술 질의",
  "message_count": 15
}
```

#### 13. History Cleared (히스토리 초기화됨)

```json
{
  "type": "history_cleared",
  "provider": "claude",
  "session": {
    "total_input_tokens": 0,
    "total_output_tokens": 0,
    "total_tokens": 0,
    "total_cost": 0,
    "request_count": 0
  }
}
```

---

### Production WebSocket Client (Handle Both Fields)

```javascript
class AgentGaiaClient {
  constructor(provider = 'claude') {
    this.provider = provider;
    this.ws = null;
    this.messageId = 0;
    this.responseBuffer = '';
  }

  connect() {
    this.ws = new WebSocket(
      `ws://localhost:9033/api/v1/ws/chat?provider=${this.provider}`
    );

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };
  }

  handleMessage(data) {
    // PRODUCTION-SAFE: Check both type and status fields
    const msgType = data.type || data.status;
    
    switch (msgType) {
      case 'connected':
        console.log(`[${data.provider}] Connected`);
        break;

      case 'streaming':
        this.responseBuffer += data.chunk;
        // Update UI progressively
        this.onStreaming(data.chunk);
        break;

      case 'complete':
        const fullResponse = this.responseBuffer;
        this.responseBuffer = '';
        this.onComplete(fullResponse);
        break;

      case 'error':
        console.error(`[${data.provider}] Error:`, data.error);
        this.onError(data.error);
        break;

      case 'backup_switch':
        console.warn(`Backup: ${data.original_provider} → ${data.backup_provider}`);
        break;

      case 'searching':
        this.onSearching(data.query);
        break;

      case 'search_results':
        this.onSearchResults(data.results);
        break;

      case 'rag_searching':
        console.log('RAG searching:', data.collection);
        break;

      case 'rag_results':
        console.log('RAG results:', data.results_count);
        break;

      case 'usage':
        console.log('Cost:', data.message.cost);
        this.onUsage(data);
        break;

      case 'conversation_created':
        console.log('New conversation:', data.conversation_id);
        break;

      case 'conversation_loaded':
        console.log('Loaded conversation:', data.title);
        break;

      case 'history_cleared':
        this.responseBuffer = '';
        console.log('History cleared');
        break;

      default:
        console.log('Unknown message:', data);
    }
  }

  // Override these methods in your UI
  onStreaming(chunk) {}
  onComplete(fullResponse) {}
  onError(error) {}
  onSearching(query) {}
  onSearchResults(results) {}
  onUsage(usageData) {}

  sendMessage(message, attachments = []) {
    this.messageId++;
    this.ws.send(JSON.stringify({
      type: 'chat',
      message: message,
      message_id: this.messageId,
      attachments: attachments
    }));
  }

  clearHistory() {
    this.ws.send(JSON.stringify({ type: 'clear_history' }));
  }

  rateResponse(rating) {
    this.ws.send(JSON.stringify({
      type: 'rating',
      message_id: this.messageId,
      rating: rating
    }));
  }

  loadConversation(conversationId) {
    this.ws.send(JSON.stringify({
      type: 'load_conversation',
      conversation_id: conversationId
    }));
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
    }
  }
}

// Usage Example
const client = new AgentGaiaClient('claude');

client.onStreaming = (chunk) => {
  // Update UI in real-time
  document.getElementById('response').textContent += chunk;
};

client.onComplete = (fullResponse) => {
  console.log('Final response:', fullResponse);
};

client.onError = (error) => {
  alert('AI Error: ' + error);
};

client.onUsage = (data) => {
  // Show real-time cost
  const costElement = document.getElementById('cost');
  costElement.textContent = `$${data.message.cost.toFixed(4)}`;
};

client.connect();

// After connection
client.sendMessage('웹에서 2025년 AI 트렌드 검색해줘');
```

---

## Chat REST API

### GET /api/v1/providers

**Purpose**: Get available LLM providers and their status.

**Response**:
```json
{
  "providers": ["claude", "openai", "gemini"],
  "models": {
    "claude": "claude-opus-4-5-20251101",
    "openai": "gpt-5.1",
    "gemini": "gemini-3-pro-preview"
  },
  "primary": "claude",
  "backup_chain": ["claude", "openai", "gemini"],
  "connected": ["claude"]
}
```

---

### GET /api/v1/health

**Purpose**: Health check for connected providers.

**Response**:
```json
{
  "status": "healthy",
  "connected_providers": ["claude", "openai"]
}
```

---

### GET /api/v1/export

**Purpose**: Export current conversation as downloadable file.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `markdown` | `markdown` or `text` |

**Response**: File download with `Content-Disposition: attachment`

**Example**:
```bash
curl "http://localhost:9033/api/v1/export?format=markdown" \
  -o conversation_20250121.md
```

---

### GET /api/v1/conversations

**Purpose**: List all saved conversations.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | Max results |
| `offset` | int | 0 | Pagination offset |

**Response**:
```json
{
  "conversations": [
    {
      "id": "uuid-string",
      "title": "AI 기술 질의",
      "created_at": "2025-01-21T10:30:00Z",
      "updated_at": "2025-01-21T11:15:00Z"
    }
  ],
  "current_conversation_id": "uuid-string"
}
```

---

### GET /api/v1/conversations/{conversation_id}

**Purpose**: Get specific conversation with all messages.

**Response**:
```json
{
  "id": "uuid-string",
  "title": "AI 기술 질의",
  "created_at": "2025-01-21T10:30:00Z",
  "updated_at": "2025-01-21T11:15:00Z",
  "messages": [
    {
      "id": "msg-uuid",
      "role": "user",
      "content": "안녕하세요",
      "provider": null,
      "model": null,
      "input_tokens": null,
      "output_tokens": null,
      "cost": null,
      "created_at": "2025-01-21T10:30:00Z"
    },
    {
      "id": "msg-uuid-2",
      "role": "assistant",
      "content": "안녕하세요! 무엇을 도와드릴까요?",
      "provider": "claude",
      "model": "claude-opus-4-5-20251101",
      "input_tokens": 15,
      "output_tokens": 20,
      "cost": 0.00175,
      "created_at": "2025-01-21T10:30:05Z"
    }
  ]
}
```

---

### DELETE /api/v1/conversations/{conversation_id}

**Purpose**: Delete a conversation.

**Response**:
```json
{
  "success": true,
  "message": "Conversation uuid-string deleted"
}
```

---

### PATCH /api/v1/conversations/{conversation_id}

**Purpose**: Update conversation title.

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | New title |

**Response**:
```json
{
  "success": true,
  "title": "새 제목"
}
```

---

## Upload API

### POST /api/v1/upload

**Purpose**: Upload single file for chat context.

**Content-Type**: `multipart/form-data`

**Request**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | File to upload |

**Supported Files**:
- Text: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.csv`
- Documents: `.pdf`, `.docx`, `.xlsx`
- Images: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`

**Response**:
```json
{
  "filename": "document.pdf",
  "category": "document",
  "mime_type": "application/pdf",
  "size": 102400,
  "success": true,
  "error": null,
  "text_length": 5000,
  "has_image": false
}
```

**Usage**: After successful upload, use `filename` in WebSocket `attachments` array.

---

### POST /api/v1/upload/multiple

**Purpose**: Upload multiple files.

**Content-Type**: `multipart/form-data`

**Request**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | File[] | Yes | File list |

**Response**: Array of `FileUploadResponse`

---

### GET /api/v1/upload

**Purpose**: List all uploaded files (current session).

**Response**:
```json
{
  "files": [
    {
      "filename": "document.pdf",
      "category": "document",
      "size": 102400,
      "has_text": true,
      "has_image": false
    }
  ]
}
```

---

### GET /api/v1/upload/{filename}

**Purpose**: Get file content for preview.

**Response**:
```json
{
  "filename": "document.pdf",
  "category": "document",
  "text_content": "Extracted text...",
  "image_base64": "base64-string",
  "image_mime_type": "image/png"
}
```

---

### DELETE /api/v1/upload/{filename}

**Purpose**: Delete a specific file.

**Response**:
```json
{
  "message": "File document.pdf deleted"
}
```

---

### DELETE /api/v1/upload

**Purpose**: Clear all uploaded files.

**Response**:
```json
{
  "message": "Cleared 3 files"
}
```

---

## Auth API

### GET /api/v1/auth/status

**Purpose**: Check current authentication status.

**Headers** (Optional):
```
Authorization: Bearer {access_token}
```

**Cookie** (Auto):
```
access_token={jwt_token}
```

**Response (Authenticated)**:
```json
{
  "authenticated": true,
  "user": {
    "id": "user-uuid",
    "email": "user@example.com",
    "name": "User Name",
    "picture": "https://example.com/avatar.jpg",
    "provider": "google"
  }
}
```

**Response (Not Authenticated)**:
```json
{
  "authenticated": false,
  "user": null
}
```

---

### GET /api/v1/auth/providers

**Purpose**: List configured OAuth providers.

**Response**:
```json
{
  "enabled": true,
  "providers": [
    {
      "name": "google",
      "display_name": "Google",
      "login_url": "/api/v1/auth/google/login"
    },
    {
      "name": "github",
      "display_name": "GitHub",
      "login_url": "/api/v1/auth/github/login"
    }
  ]
}
```

---

### GET /api/v1/auth/google/login

**Purpose**: Start Google OAuth flow.

**Response**: Redirect to Google OAuth consent page.

**After Success**: Redirects to `/?auth_success=true` with `access_token` cookie.

**After Error**: Redirects to `/?auth_error={error}`.

---

### GET /api/v1/auth/github/login

**Purpose**: Start GitHub OAuth flow.

**Response**: Redirect to GitHub OAuth consent page.

---

### POST /api/v1/auth/logout

**Purpose**: Logout and clear cookies.

**Response**:
```json
{
  "message": "Logged out successfully"
}
```

---

## Root Endpoints

### GET /

**Purpose**: Main chat interface (HTML).

**Response**: `text/html` - Rendered via Jinja2 template

---

### GET /health

**Purpose**: Full service health check.

**Response**:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "local",
  "providers": {
    "anthropic": true,
    "openai": true,
    "google": true
  }
}
```

---

## Global Error Responses

### Standard Error Format

```json
{
  "detail": "Error message here"
}
```

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request - Invalid parameters |
| 401 | Unauthorized - Authentication required |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - OAuth not configured |

---

## LLM Cost Information

### Real-Time Cost Tracking

Costs are calculated **per message** and accumulated per session.

| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| claude-opus-4-5-20251101 | $0.015 | $0.075 |
| claude-sonnet-4-20250514 | $0.003 | $0.015 |
| gpt-5.1 | $0.01 | $0.03 |
| gpt-4o | $0.0025 | $0.01 |
| gemini-3-pro-preview | $0.00125 | $0.005 |
| gemini-2.0-flash | $0.0001 | $0.0004 |

**Example Calculation**:
- 150 input tokens + 200 output tokens with Claude Opus 4.5
- Cost: (150/1000 × $0.015) + (200/1000 × $0.075) = $0.02625

---

## Production Deployment Checklist

### Environment Variables Required

```bash
# Core
APP_ENV=prod

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Vault (Recommended for API keys)
VAULT_TOKEN=your-token
VAULT_URL=http://vault:8200

# OAuth Providers (Optional)
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...

# Direct API Keys (Alternative to Vault)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

### Security Recommendations

1. **Use Vault** for API key management (enabled by default)
2. **HTTPS only** in production (set `secure` cookies)
3. **CORS** restrict origins in production
4. **Rate limiting** via reverse proxy (nginx/haproxy)
5. **Database connection pooling** configured

---

## 🚀 Quick UI Development Guide

### Multi-Provider Streaming UI Architecture

```javascript
// Manage multiple WebSocket connections
class MultiProviderChat {
  constructor() {
    this.providers = ['claude', 'openai', 'gemini'];
    this.clients = {};
  }

  connectAll() {
    this.providers.forEach(provider => {
      const client = new AgentGaiaClient(provider);
      client.onStreaming = (chunk) => this.updateUI(provider, chunk);
      client.onComplete = (response) => this.finalize(provider, response);
      client.connect();
      this.clients[provider] = client;
    });
  }

  broadcastMessage(message) {
    // Send same message to ALL providers simultaneously
    Object.values(this.clients).forEach(client => {
      client.sendMessage(message);
    });
  }

  updateUI(provider, chunk) {
    const el = document.getElementById(`response-${provider}`);
    el.textContent += chunk;
  }

  finalize(provider, response) {
    console.log(`${provider} finished:`, response);
    // Enable rating, update costs, etc.
  }
}

// Usage
const chat = new MultiProviderChat();
chat.connectAll();

// Send to all providers
chat.broadcastMessage("한국의 주식 시장 전망 알려줘");

// Watch all three responses stream in real-time!
```

---

## Troubleshooting

### WebSocket Connection Issues

```javascript
ws.onerror = (error) => {
  console.error('WS Error:', error);
  // Check: 1) Provider API key exists 2) Network stable 3) Vault token valid
};
```

### File Upload Issues

- **Max size**: Check server config (default: unlimited, set by reverse proxy)
- **Unsupported type**: See supported list above
- **Processing large PDFs**: May take 5-10 seconds for 80+ pages

### Authentication Issues

- **OAuth not configured**: Returns 503 error
- **State mismatch**: Clear cookies and retry
- **Token expired**: Auto-handled by session middleware

---

**Document Version**: 1.1.0 (Production-Ready)  
**Based On**: Actual Implementation (Source Code Verified)  
**Last Verified**: 2025-01-21 15:30:00+09:00

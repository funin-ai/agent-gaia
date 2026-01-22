# AgentGaia API Documentation

**Base URL**: `http://localhost:9033`
**Version**: 0.1.0

---

## Table of Contents

1. [WebSocket API](#websocket-api) - 실시간 채팅 (핵심)
2. [Chat REST API](#chat-rest-api) - 대화 관리
3. [Upload API](#upload-api) - 파일 업로드
4. [Auth API](#auth-api) - OAuth 인증

---

## WebSocket API

### Connect

```
ws://localhost:9033/api/v1/ws/chat?provider={provider}
```

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `provider` | string | Yes | LLM 프로바이더: `claude`, `openai`, `gemini` |

**Example**:
```javascript
const ws = new WebSocket('ws://localhost:9033/api/v1/ws/chat?provider=claude');
```

---

### Client → Server Messages

#### 1. Chat Message (채팅 전송)

```json
{
  "type": "chat",
  "message": "안녕하세요",
  "message_id": 1,
  "attachments": ["document.pdf", "image.png"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | 고정값: `"chat"` |
| `message` | string | Yes | 사용자 메시지 |
| `message_id` | int | No | 메시지 추적용 ID (기본값: 0) |
| `attachments` | string[] | No | 첨부 파일명 목록 (사전 업로드 필요) |

#### 2. Rating (응답 평가)

```json
{
  "type": "rating",
  "message_id": 1,
  "rating": 5
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | Yes | 고정값: `"rating"` |
| `message_id` | int | Yes | 평가할 메시지 ID |
| `rating` | int | Yes | 평점 (1-5) |

#### 3. Clear History (대화 초기화)

```json
{
  "type": "clear_history"
}
```

#### 4. Load Conversation (대화 불러오기)

```json
{
  "type": "load_conversation",
  "conversation_id": "uuid-string"
}
```

---

### Server → Client Messages

#### 1. Connected (연결 확인)

```json
{
  "type": "connected",
  "provider": "claude",
  "status": "ready"
}
```

#### 2. Streaming (스트리밍 응답)

```json
{
  "provider": "claude",
  "status": "streaming",
  "chunk": "안녕"
}
```

> **Note**: 여러 청크가 순차적으로 전송됨. 클라이언트에서 누적하여 표시.

#### 3. Complete (응답 완료)

```json
{
  "provider": "claude",
  "status": "complete",
  "total_tokens": null
}
```

#### 4. Error (에러)

```json
{
  "provider": "claude",
  "status": "error",
  "error": "Error message here",
  "backup_provider": "openai"
}
```

#### 5. Backup Switch (백업 프로바이더 전환)

```json
{
  "type": "backup_switch",
  "original_provider": "claude",
  "backup_provider": "openai",
  "reason": "Rate limit exceeded"
}
```

#### 6. Searching (웹 검색 시작)

```json
{
  "type": "searching",
  "provider": "claude",
  "query": "검색 쿼리"
}
```

#### 7. Search Results (웹 검색 결과)

```json
{
  "type": "search_results",
  "provider": "claude",
  "query": "검색 쿼리",
  "results": [
    {
      "title": "Result Title",
      "url": "https://example.com",
      "snippet": "Result snippet..."
    }
  ],
  "has_results": true
}
```

#### 8. RAG Searching (RAG 검색 시작)

```json
{
  "type": "rag_searching",
  "provider": "claude",
  "collection": "homepage_collection"
}
```

#### 9. RAG Results (RAG 검색 결과)

```json
{
  "type": "rag_results",
  "provider": "claude",
  "collection": "homepage_collection",
  "results_count": 5,
  "processing_time_ms": 123.45
}
```

#### 10. Usage (토큰 사용량)

```json
{
  "type": "usage",
  "provider": "claude",
  "model": "claude-opus-4-5-20251101",
  "message": {
    "input_tokens": 150,
    "output_tokens": 200,
    "total_tokens": 350,
    "cost": 0.000525
  },
  "session": {
    "total_input_tokens": 500,
    "total_output_tokens": 800,
    "total_tokens": 1300,
    "total_cost": 0.00195,
    "request_count": 3
  },
  "conversation_id": "uuid-string"
}
```

#### 11. Conversation Created (새 대화 생성됨)

```json
{
  "type": "conversation_created",
  "provider": "claude",
  "conversation_id": "uuid-string",
  "title": "대화 제목"
}
```

#### 12. Conversation Loaded (대화 불러옴)

```json
{
  "type": "conversation_loaded",
  "provider": "claude",
  "conversation_id": "uuid-string",
  "title": "대화 제목",
  "message_count": 10
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

### WebSocket 연결 예제 (JavaScript)

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

    this.ws.onopen = () => {
      console.log(`Connected to ${this.provider}`);
    };

    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      this.handleMessage(data);
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    this.ws.onclose = () => {
      console.log('Disconnected');
    };
  }

  handleMessage(data) {
    switch (data.type || data.status) {
      case 'connected':
        console.log('Ready to chat');
        break;

      case 'streaming':
        this.responseBuffer += data.chunk;
        // Update UI with partial response
        break;

      case 'complete':
        console.log('Response complete:', this.responseBuffer);
        this.responseBuffer = '';
        break;

      case 'error':
        console.error('Error:', data.error);
        break;

      case 'backup_switch':
        console.warn(`Switched from ${data.original_provider} to ${data.backup_provider}`);
        break;

      case 'usage':
        console.log('Tokens used:', data.message.total_tokens);
        console.log('Cost:', data.message.cost);
        break;

      case 'searching':
        console.log('Searching web for:', data.query);
        break;

      case 'rag_searching':
        console.log('Searching knowledge base:', data.collection);
        break;
    }
  }

  sendMessage(message, attachments = []) {
    this.messageId++;
    this.ws.send(JSON.stringify({
      type: 'chat',
      message: message,
      message_id: this.messageId,
      attachments: attachments
    }));
  }

  rateResponse(rating) {
    this.ws.send(JSON.stringify({
      type: 'rating',
      message_id: this.messageId,
      rating: rating
    }));
  }

  clearHistory() {
    this.ws.send(JSON.stringify({
      type: 'clear_history'
    }));
  }

  loadConversation(conversationId) {
    this.ws.send(JSON.stringify({
      type: 'load_conversation',
      conversation_id: conversationId
    }));
  }
}

// Usage
const client = new AgentGaiaClient('claude');
client.connect();

// After connection established
client.sendMessage('안녕하세요! 오늘 날씨 어때요?');
```

---

## Chat REST API

### GET /api/v1/providers

사용 가능한 LLM 프로바이더 목록 조회.

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

### GET /api/v1/health

헬스 체크.

**Response**:
```json
{
  "status": "healthy",
  "connected_providers": ["claude", "openai"]
}
```

### GET /api/v1/export

대화 내보내기 (Markdown 또는 Text).

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `format` | string | `markdown` | 내보내기 형식: `markdown`, `text` |

**Response**: 파일 다운로드 (Content-Disposition: attachment)

### GET /api/v1/conversations

대화 목록 조회.

**Query Parameters**:
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 50 | 최대 결과 수 |
| `offset` | int | 0 | 페이지네이션 오프셋 |

**Response**:
```json
{
  "conversations": [
    {
      "id": "uuid-string",
      "title": "대화 제목",
      "created_at": "2024-01-15T10:30:00Z",
      "updated_at": "2024-01-15T11:00:00Z"
    }
  ],
  "current_conversation_id": "uuid-string"
}
```

### GET /api/v1/conversations/{conversation_id}

특정 대화 상세 조회.

**Response**:
```json
{
  "id": "uuid-string",
  "title": "대화 제목",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:00:00Z",
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
      "created_at": "2024-01-15T10:30:00Z"
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
      "created_at": "2024-01-15T10:30:05Z"
    }
  ]
}
```

### DELETE /api/v1/conversations/{conversation_id}

대화 삭제.

**Response**:
```json
{
  "success": true,
  "message": "Conversation uuid-string deleted"
}
```

### PATCH /api/v1/conversations/{conversation_id}

대화 제목 수정.

**Query Parameters**:
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `title` | string | Yes | 새 제목 |

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

단일 파일 업로드.

**Content-Type**: `multipart/form-data`

**Request**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | File | Yes | 업로드할 파일 |

**Supported File Types**:
- Text: `.txt`, `.md`, `.py`, `.js`, `.ts`, `.json`, `.yaml`, `.yml`, `.csv`
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

### POST /api/v1/upload/multiple

다중 파일 업로드.

**Content-Type**: `multipart/form-data`

**Request**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | File[] | Yes | 업로드할 파일 목록 |

**Response**: `FileUploadResponse[]` 배열

### GET /api/v1/upload

업로드된 파일 목록 조회.

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
    },
    {
      "filename": "image.png",
      "category": "image",
      "size": 50000,
      "has_text": false,
      "has_image": true
    }
  ]
}
```

### GET /api/v1/upload/{filename}

업로드된 파일 컨텍스트 조회.

**Response**:
```json
{
  "filename": "document.pdf",
  "category": "document",
  "text_content": "Extracted text content...",
  "image_base64": null,
  "image_mime_type": null
}
```

### DELETE /api/v1/upload/{filename}

업로드된 파일 삭제.

**Response**:
```json
{
  "message": "File document.pdf deleted"
}
```

### DELETE /api/v1/upload

모든 업로드 파일 삭제.

**Response**:
```json
{
  "message": "Cleared 3 files"
}
```

---

## Auth API

### GET /api/v1/auth/status

인증 상태 확인.

**Headers** (Optional):
```
Authorization: Bearer {access_token}
```

**Or Cookie**:
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

### GET /api/v1/auth/providers

사용 가능한 OAuth 프로바이더 목록.

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

### GET /api/v1/auth/google/login

Google OAuth 로그인 시작.

**Response**: Redirect to Google OAuth consent page

### GET /api/v1/auth/google/callback

Google OAuth 콜백 (내부용).

**Response**: Redirect to frontend with `?auth_success=true` or `?auth_error={error}`

### GET /api/v1/auth/github/login

GitHub OAuth 로그인 시작.

**Response**: Redirect to GitHub OAuth consent page

### GET /api/v1/auth/github/callback

GitHub OAuth 콜백 (내부용).

**Response**: Redirect to frontend with `?auth_success=true` or `?auth_error={error}`

### POST /api/v1/auth/logout

로그아웃 (쿠키 삭제).

**Response**:
```json
{
  "message": "Logged out successfully"
}
```

---

## Root Endpoints

### GET /

메인 페이지 (HTML).

**Response**: `text/html` - Jinja2 템플릿 렌더링

### GET /health

전체 서비스 헬스 체크.

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

## Error Responses

모든 API는 에러 시 다음 형식을 반환합니다:

```json
{
  "detail": "Error message here"
}
```

**HTTP Status Codes**:
| Code | Description |
|------|-------------|
| 400 | Bad Request - 잘못된 요청 |
| 401 | Unauthorized - 인증 필요 |
| 404 | Not Found - 리소스 없음 |
| 500 | Internal Server Error - 서버 에러 |
| 503 | Service Unavailable - OAuth 미설정 등 |

---

## LLM 비용 정보 (Config)

| Model | Input (per 1K tokens) | Output (per 1K tokens) |
|-------|----------------------|------------------------|
| claude-opus-4-5-20251101 | $0.015 | $0.075 |
| claude-sonnet-4-20250514 | $0.003 | $0.015 |
| gpt-5.1 | $0.01 | $0.03 |
| gpt-4o | $0.0025 | $0.01 |
| gemini-3-pro-preview | $0.00125 | $0.005 |
| gemini-2.0-flash | $0.0001 | $0.0004 |

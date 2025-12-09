# Task 1: LLM Router + Vault API Key 관리 + PDF 파싱 + 3-분할 WebSocket

**Phase**: Week 1 MVP  
**우선순위**: Highest  
**예상 소요 시간**: 1일 (금요일)  
**담당**: Claude Code (구현) / Kimi (검증)

---

## 🎯 목표

지난주 RFP 분석을 위한 기반 인프라 구축:
1. **보안**: Vault에서 API Key 안전하게 관리 및 로드
2. **유연성**: 3개 Provider (Claude/GPT/Gemini) 동적 라우팅 + 자동 백업
3. **입력**: 80-120페이지 PDF 파일 파싱 (민감정보 없는 버전)
4. **출력**: 3개 LLM이 동시 분석할 수 있는 WebSocket 인프라

시연 시나리오: "RFP를 AI 3명에게 동시에 분석시켰습니다"

---

## 📋 구현 범위

### 1. Vault API Key 관리

**위치**: `src/core/settings.py`

```python
import hvac
from pydantic_settings import BaseSettings

class VaultConfig(BaseModel):
    url: str = "http://localhost:8201"
    token: str = ""  # VAULT_TOKEN 환경변수
    secret_path: str = "secret/data/ai-chat/llm-keys"

class Settings(BaseSettings):
    app_env: str = "local"
    use_vault: bool = False
    vault: VaultConfig = VaultConfig()
    
    def load_api_keys(self) -> dict[str, str]:
        """Vault 또는 환경변수에서 API 키 로드"""
        if self.use_vault:
            client = hvac.Client(url=self.vault.url, token=self.vault.token)
            return client.read(self.vault.secret_path)["data"]["data"]
        else:
            return {
                "anthropic": os.getenv("ANTHROPIC_API_KEY"),
                "openai": os.getenv("OPENAI_API_KEY"),
                "google": os.getenv("GOOGLE_API_KEY"),
            }
```

**설정 파일**: `config/config-local.yml`
```yaml
vault:
  url: "http://localhost:8201"
  token: "${VAULT_TOKEN}"
  secret_path: "secret/data/ai-chat/llm-keys"

llm:
  primary_provider: "claude"
  backup_chain: ["claude", "openai", "gemini"]
  models:
    claude: "claude-opus-4-5-20251101"
    openai: "gpt-5.1"
    gemini: "gemini-3-pro-preview"
```

**검증 항목**:
- [ ] Vault 연결 성공 (localhost:8201)
- [ ] API 키 로드 성공 (3개 Provider: anthropic, openai, google)
- [ ] 백업 체인 순환 로직 정상 작동
- [ ] 실패 시 자동 전환 (+ 로그 기록)

---

### 2. LLM Router (Claude Opus 4.5 지원)

**위치**: `src/core/llm_router.py`

```python
from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

PROVIDER_CONFIG = {
    "claude": {
        "model": "claude-opus-4-5-20251101",
        "client_class": ChatAnthropic,
        "api_key_name": "anthropic",
        "cost_per_1k": 0.075
    },
    "openai": {
        "model": "gpt-5.1",
        "client_class": ChatOpenAI,
        "api_key_name": "openai",
        "cost_per_1k": 0.01
    },
    "gemini": {
        "model": "gemini-3-pro-preview",
        "client_class": ChatGoogleGenerativeAI,
        "api_key_name": "google",
        "cost_per_1k": 0.00125
    }
}

class LLMRouter:
    def __init__(self, settings: Settings):
        self.api_keys = settings.load_api_keys()
        self.backup_chain = settings.llm.backup_chain
    
    def get_llm(self, provider: str, use_backup: bool = True):
        """Provider별 LLM 인스턴스 생성 + 백업 준비"""
        try:
            config = PROVIDER_CONFIG[provider]
            api_key = self.api_keys.get(config["api_key_name"])

            return config["client_class"](
                model=config["model"],
                api_key=api_key,
                streaming=True,
                max_tokens=8192,
                temperature=0.2
            )
        except Exception as e:
            if use_backup:
                return self._try_backup(provider)
            raise
    
    def _try_backup(self, failed_provider: str):
        """백업 체인에서 다음 Provider 시도"""
        idx = self.backup_chain.index(failed_provider)
        for backup in self.backup_chain[idx+1:]:
            try:
                return self.get_llm(backup, use_backup=False)
            except:
                continue
        raise RuntimeError("모든 백업 Provider 실패")
```

**Rate Limit 처리** (`src/core/retry.py`):
```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from openai import RateLimitError as OpenAIRateLimitError
from anthropic import RateLimitError as AnthropicRateLimitError
from google.api_core.exceptions import ResourceExhausted

# 재시도 데코레이터
llm_retry = retry(
    retry=retry_if_exception_type((
        OpenAIRateLimitError,
        AnthropicRateLimitError,
        ResourceExhausted
    )),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(3),
    reraise=True
)

# 사용 예시
class LLMRouter:
    @llm_retry
    async def call_with_retry(self, provider: str, messages: list):
        llm = self.get_llm(provider)
        return await llm.ainvoke(messages)
```

**검증 항목**:
- [ ] Claude Opus 4.5 호출 성공
- [ ] 잘못된 키로 테스트 시 백업 전환
- [ ] Rate Limit(60rpm) 초과 시 tenacity 재시도 동작
- [ ] 스트리밍 응답 정상 작동

---

### 3. PDF 파싱

**위치**: `src/utils/pdf_parser.py`

```python
import pdfplumber
import re

class PDFParser:
    def __init__(self, max_pages: int = 120):
        self.max_pages = max_pages

    def extract_text(self, file_path: str) -> str:
        """PDF 파싱"""
        text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages[:self.max_pages]:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n\n"

        return text.strip()
    
    def get_metadata(self, file_path: str) -> dict:
        """PDF 메타데이터 추출"""
        with pdfplumber.open(file_path) as pdf:
            return {
                "pages": len(pdf.pages),
                "size": pdf.metadata.get("File size", "Unknown")
            }
```

**RFP 샘플 준비**:
```bash
config/samples/
├── rfp_small_30p.pdf      # 테스트용
├── rfp_medium_80p.pdf     # 시연용 (주력)
└── rfp_large_120p.pdf     # 스트레스 테스트
```

**검증 항목**:
- [ ] PDF 파싱 정상 작동 (80~120페이지)
- [ ] 특수 문자/표 처리 오류 없음

---

### 4. 3-분할 WebSocket

**위치**: `src/api/routes/chat.py`

```python
from fastapi import WebSocket, WebSocketDisconnect
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}
    
    async def connect(self, provider: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[provider] = websocket
    
    def disconnect(self, provider: str):
        self.active_connections.pop(provider, None)
    
    async def broadcast_progress(self, message: dict):
        """모든 클라이언트에 진행상황 브로드캐스트"""
        for connection in self.active_connections.values():
            await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, provider: str):
    """
    파라미터:
    - provider: claude | openai | gemini
    
    메시지 형식:
    {"type": "analyze", "file_id": "uuid", "prompt": "..."}
    {"type": "user_rating", "rating": 4}
    """
    await manager.connect(provider, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "analyze":
                # 비동기 분석 시작
                asyncio.create_task(
                    analyze_rfp(provider, data["file_id"], data["prompt"])
                )
            
            elif data["type"] == "user_rating":
                # 별점 저장
                state.evaluation.user_ratings[provider] = data["rating"]
    
    except WebSocketDisconnect:
        manager.disconnect(provider)

async def analyze_rfp(provider: str, file_id: str, prompt: str):
    """실제 LLM 분석 실행"""
    try:
        # LLM 인스턴스 가져오기
        llm = llm_router.get_llm(provider)
        
        # PDF 내용 로드
        file_content = file_store.get(file_id)
        
        # 스트리밍 시작
        async for chunk in llm.astream(
            f"다음 RFP를 분석하세요:\n\n{file_content}\n\n{prompt}"
        ):
            await manager.broadcast_progress({
                "provider": provider,
                "status": "streaming",
                "chunk": chunk.content
            })
        
        # 완료
        await manager.broadcast_progress({
            "provider": provider,
            "status": "complete"
        })
    
    except Exception as e:
        # 실패 시 백업 전환
        backup_llm = llm_router.get_llm(provider, use_backup=True)
        # ... 재시도 로직
```

**위치**: `static/js/chat.js`

```javascript
// 3개 WebSocket 동시 연결
const connections = {
    claude: new WebSocket('ws://localhost:8000/ws/chat?provider=claude'),
    openai: new WebSocket('ws://localhost:8000/ws/chat?provider=openai'),
    gemini: new WebSocket('ws://localhost:8000/ws/chat?provider=gemini')
};

// 각 연결에 대한 핸들러
Object.keys(connections).forEach(provider => {
    const ws = connections[provider];
    const container = document.getElementById(`${provider}-output`);
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.status === 'streaming') {
            container.innerHTML += data.chunk;
        } else if (data.status === 'complete') {
            container.classList.add('complete');
            updateScore(provider, data.score);
        }
    };
});

// 분석 시작 함수
function startAnalysis() {
    const fileId = document.getElementById('file-id').value;
    
    Object.entries(connections).forEach(([provider, ws]) => {
        ws.send(JSON.stringify({
            type: 'analyze',
            file_id: fileId,
            prompt: '이 RFP의 핵심 요구사항 5가지를 분석하고 제안서 초안을 작성하세요.'
        }));
    });
}

// 별점 전송
function sendRating(provider, rating) {
    connections[provider].send(JSON.stringify({
        type: 'user_rating',
        rating: rating
    }));
}
```

**UI 구조** (`templates/index.html`):
```html
<div class="grid">
  <div class="column">
    <h3>Claude Opus 4.5</h3>
    <div id="claude-output" class="output"></div>
    <div class="star-rating" data-provider="claude"></div>
  </div>

  <div class="column">
    <h3>GPT-5.1</h3>
    <div id="openai-output" class="output"></div>
    <div class="star-rating" data-provider="openai"></div>
  </div>

  <div class="column">
    <h3>Gemini 3 Pro</h3>
    <div id="gemini-output" class="output"></div>
    <div class="star-rating" data-provider="gemini"></div>
  </div>
</div>
```

**검증 항목**:
- [ ] 3개 WebSocket 동시 연결 성공
- [ ] 토큰별 스트리밍 실시간 표시
- [ ] 한 개 실패 시 나머지 2개 정상 작동
- [ ] 백업 전환 시 UI에 알림 표시
- [ ] 별점 클릭 시 서버에 정상 전송

---

## 📦 의존성 및 설정

**pyproject.toml**:
```toml
[project]
name = "agent-gaia"
version = "0.1.0"
dependencies = [
    "fastapi[standard]>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "langgraph>=0.2.0",
    "langchain-anthropic>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-google-genai>=2.0.0",
    "pydantic-settings>=2.0.0",
    "pyyaml>=6.0",
    "hvac>=2.0.0",              # Vault
    "tenacity>=8.2.0",          # Rate Limit 재시도
    "pdfplumber>=0.10.0",       # PDF 파싱
    "python-docx>=1.1.0",       # Word 생성
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-asyncio>=0.21.0"]
```

**환경 설정** (`.env.example`):
```bash
# Vault 연결 (시연 필수)
VAULT_TOKEN=myroot
VAULT_URL=http://localhost:8201

# 로컬 개발용 (Vault 없을 시)
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=...
```

**실행 명령어**:
```bash
# 설치
uv sync

# 실행
export VAULT_TOKEN=myroot
uv run run.py --local --use-vault

# 접속
open http://localhost:8000
```

---

## ✅ 검증 기준 (KIMI 검증용)

### 기능 검증
- [ ] **Vault**: 3개 API 키 모두 로드 성공 (anthropic, openai, google)
- [ ] **LLM Router**: Claude Opus 4.5 호출 성공
- [ ] **Backup**: 잘못된 키로 테스트 시 자동 전환
- [ ] **PDF Parser**: PDF 파싱 정상 작동
- [ ] **WebSocket**: 3개 동시 연결, 실시간 스트리밍
- [ ] **Star Rating**: 별점 클릭 → 서버 저장 확인

### 성능 검증
- [ ] 메모리 사용량 < 500MB (3개 WebSocket)
- [ ] WebSocket 메시지 latency < 100ms

### 보안 검증
- [ ] API 키가 로그/에러 메시지에 노출되지 않음
- [ ] .env 파일 Git 추적 안됨 (.gitignore 확인)
- [ ] 업로드된 PDF 임시 저장소 암호화 (선택사항)

---

## 🎯 시연 테스트 시나리오

### 시나리오 1: 정상 작동
```
1. config/samples/rfp_medium_80p.pdf 업로드
2. 3개 LLM 동시 분석 시작
3. 실시간 스트리밍 확인 (3개 분할)
4. 각 모델별 별점 3-5개 입력
5. 분석 완료 후 점수 확인
```

### 시나리오 2: 백업 전환
```
1. Vault에서 Claude 키 임시 삭제
2. 업로드 후 분석 시작
3. UI에 "Claude 연결 실패 → GPT-4o 전환" 알림 표시
4. GPT-4o가 Claude 역할 대신 수행
```

### 시나리오 3: 대용량 PDF
```
1. config/samples/rfp_large_120p.pdf 업로드
2. 파싱 및 분석 정상 작동 확인
```

---

## 🔍 위험 요소 및 대응

| 위험 | 확률 | 영향 | 대응 |
|------|------|------|------|
| Vault 연결 실패 | 중 | 높 | 로컬 .env 백업 모드 준비 |
| PDF 파싱 지연 (30초+) | 낮 | 중 | 미리 파싱된 텍스트 캐시 |
| WebSocket 연결 끊김 | 중 | 중 | 자동 재연결 + 진행상황 복원 |
| Rate Limit 초과 | 중 | 높 | 요청 간 1초 지연, 캐시 활용 |
| 3개 모델 동시 장애 | 낮 | 높 | 로컬 Ollama 모델 준비 |

**총괄 검증자**: KIMI
**구현 완료 후 검증 항목**: 위 검증 기준 모두 체크

---

**다음 작업**: 이 설계서를 바탕으로 Claude Code가 구현 시작  
**검증 시점**: 구현 완료 후 KIMI가 코드 리뷰 및 테스트 수행
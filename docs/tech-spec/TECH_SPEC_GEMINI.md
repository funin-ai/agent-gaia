AgentGaia — Technical Specification V6.0The Self-Evolving Conversational Agent PlatformVersion: 6.0 (Execution Baseline)Date: 2025-12-03Status: Ready for DevelopmentEngine: LangGraph + Python 3.11+Architectural Pattern: Dynamic Graph Generation & Orchestration1. Executive Summary (개요)1.1 Product DefinitionAgentGaia는 도메인 전문가(투자자, 변호사, 연구원)가 코딩 없이 자연어로 자신의 업무 프로세스를 설명하면, 이를 실행 가능한 LangGraph 워크플로우로 실시간 변환하고 실행하는 온프레미스(On-Premise) 기반 AI 에이전트 플랫폼입니다.1.2 Core Philosophy (핵심 철학)Zero Programming: 사용자는 노드, 엣지, JSON을 보지 않습니다. 오직 "설명"할 뿐입니다.Explainable Execution: 시스템은 실행 과정을 블랙박스가 아닌 자연어로 실시간 중계합니다.Self-Hosted First: 데이터 주권 보호를 위해 Docker Compose 기반의 온프레미스 배포를 최우선으로 합니다.Architectural Evolution: 초기에는 인간이 정의한 도구를 사용하지만, 아키텍처적으로는 시스템이 스스로 도구를 생성(Code Generation)할 수 있는 **슬롯(Slot)**과 데이터 파이프라인을 미리 확보합니다.1.3 Scope & Boundaries (What We Are NOT)Not a No-Code Tool: 드래그 앤 드롭 UI를 제공하지 않습니다. 대화형 인터페이스(Chat UI)가 유일한 입력 도구입니다.Not a General Chatbot: 잡담을 위한 챗봇이 아닙니다. 명확한 'Task'와 'Goal'이 있는 워크플로우 생성기입니다.Not a SaaS Only: 고객의 데이터를 중앙 서버에 저장하지 않는 것을 기본 아키텍처 원칙으로 합니다.2. System Architecture (시스템 아키텍처)시스템은 4-Layer Architecture를 따르며, 각 계층은 독립적으로 동작하되 유기적으로 연결됩니다.Layer 1: Conversational Interface (UX)Tech: Next.js 15, WebSocket, React Flow (Read-only Visualization)Role: 사용자 의도 파악 및 Progressive Clarification(점진적 구체화) 수행.Key Feature: 워크플로우가 생성되는 과정을 시각적으로 보여주되, 수정은 대화로만 수행합니다.Layer 2: Intelligence Core (Brain)Tech: FastAPI, Pydantic v2, LLM RouterRole: 자연어를 구조화된 명세(Spec)로 변환합니다.Components:Intent Parser: 모호한 자연어 → Intent 객체 (Goal, Constraints, Missing Info) 변환.Graph Synthesizer: Intent + Agent Registry → LangGraph StateGraph 코드 생성.Meta-Cognition Hook: 매칭되는 Agent가 없을 때 '결핍(Gap)'을 감지하고 로그를 남기는 로직 (진화의 씨앗).Layer 3: LangGraph Runtime (Engine)Tech: LangGraph, PostgresCheckpointerRole: 생성된 그래프의 컴파일, 실행, 상태 관리, 복구.Key Features:Dynamic Compilation: 정적 코드가 아닌, 런타임에 Node 클래스들을 조합하여 StateGraph 인스턴스를 동적 생성.Human-in-the-Loop: interrupt_before 기능을 사용해 중요 실행(송금, 계약서 발송 등) 전 사용자 승인 대기.Event Streaming: astream_events를 통해 노드 진입/완료 이벤트를 NATS로 발행.Layer 4: Infrastructure & Sandbox (Body)Tech: Docker, NATS JetStream, Redis, HashiCorp VaultRole: 실제 코드 실행 및 외부 시스템 연결 격리.Security:Network Allowlist: 승인된 도메인(예: api.eodhd.com) 외 아웃바운드 트래픽 차단.Resource Quota: 컨테이너당 CPU/Memory 제한 설정.3. Data Models & Specifications (데이터 명세)3.1 Intent Definition (Pydantic)사용자의 자연어 발화는 반드시 아래 구조체로 변환되어야 합니다.class Intent(BaseModel):
    domain: Literal["finance", "legal", "research", "general"]
    goal: str                        # 예: "매일 아침 9시 브리핑"
    tasks: List[str]                 # 예: ["데이터 수집", "분석", "슬랙 전송"]
    constraints: List[Constraint]    # 예: [{"type": "time", "val": "09:00"}]
    required_capabilities: List[str] # 예: ["market_data", "llm_summary", "slack"]
    ambiguities: List[str]           # 사용자에게 되물어야 할 질문 리스트
3.2 Agent Registry Schema시스템이 사용할 수 있는 도구(Agent)의 정의입니다. PostgreSQL의 pgvector를 활용해 Semantic Search를 수행합니다.CREATE TABLE agent_registry (
    id UUID PRIMARY KEY,
    name VARCHAR(50) UNIQUE,
    description TEXT,                -- LLM이 검색(Semantic Search)할 때 사용
    capabilities TEXT[],             -- 기능 태그
    input_schema JSONB,              -- Pydantic JSON Schema
    output_schema JSONB,
    cost_per_run DECIMAL(10, 4),     -- 실행 비용 추산
    is_safe BOOLEAN DEFAULT FALSE,   -- Human Approval 필요 여부 (True면 자동 실행)
    docker_image VARCHAR(100)        -- 실행할 컨테이너 이미지
);
4. Key Functional Requirements (핵심 기능 명세)4.1 Workflow Synthesis Logic (The "Magic")Input: Intent 객체 수신.Retrieval: required_capabilities 벡터 검색을 통해 agent_registry에서 적합한 Agent 후보군(Top-K) 추출.Graph Construction:LLM(Claude-Sonnet)이 Agent들의 입/출력 스키마를 분석하여 연결 순서(Sequential, Parallel) 결정.LangGraph의 StateGraph 객체에 add_node, add_edge 메소드를 호출하여 그래프 조립.Validation: 그래프의 순환 참조(Cycle) 및 고립된 노드(Isolated Node) 유효성 검사.Compilation: graph.compile(checkpointer=postgres_saver) 호출하여 Runnable 객체 생성.4.2 Human-in-the-Loop (HIL) ImplementationTrigger: 사용하는 Agent의 is_safe 플래그가 False이거나, 사용자가 명시적으로 "확인 후 실행해줘"라고 요청했을 때.Mechanism:# LangGraph Node Logic
def approval_node(state):
    return Command(
        interrupt=True, 
        resume="approved" # Resume 시 받을 값의 키
    )
UX Flow: 채팅창에 "승인 요청" 버튼 렌더링 → 사용자 클릭 → API 호출 → 워크플로우 resume.4.3 Self-Evolution Readiness (Architectural Hook)Current Scope: Synthesizer가 적절한 Agent를 찾지 못하면 "죄송합니다, 해당 기능(Capability)이 없습니다."라고 응답하고 구조화된 로그를 남깁니다.Future Hook: 이 로그(CapabilityGapEvent)는 추후 Meta-Agent가 새로운 Agent 코드를 생성(Code Gen)하는 트리거가 됩니다. 현재 단계에서는 데이터 수집에 집중합니다.5. Technology Stack & Deployment (기술 스택)5.1 Tech Stack TableComponentTechnologyRationaleBackendPython 3.11+, FastAPIAI/ML 라이브러리 생태계 최적화, 비동기 지원WorkflowLangGraph순환 그래프, Persistence, Streaming 기본 지원 (필수)DatabasePostgreSQL (v16)JSONB 지원(상태 저장), pgvector(유사도 검색)Event BusNATS JetStreamMSA 통신 및 대용량 로그 스트리밍CacheRedisAPI Rate Limiting, 단기 세션, 분산 락LLMClaude 3.5 Sonnet / GPT-4o복잡한 추론 및 코드 생성 능력 (Main Brain)Local LLMOllama (Llama 3.1)개발 환경 및 단순 작업용 비용 절감 옵션5.2 Deployment Strategy (Docker All-in-One)개발자의 쉬운 진입을 위해 단일 docker-compose.yml 배포를 지원합니다.version: '3.8'
services:
  agentgaia-core:
    image: agentgaia/core:latest
    environment:
      - DATABASE_URL=postgres://user:pass@postgres:5432/agentgaia
      - LLM_PROVIDER=anthropic
      - VAULT_URL=http://vault:8200
    depends_on:
      - postgres
      - redis
      - nats
    security_opt:
      - no-new-privileges:true
  
  postgres:
    image: postgres:16
    volumes:
      - pgdata:/var/lib/postgresql/data
6. Security & Stability Protocols (보안 및 안정성)6.1 Safety GuardrailsNo Exec/Eval: 어떠한 경우에도 exec(), eval(), os.system() 사용은 정적 분석 단계(AST Parsing)에서 원천 차단됩니다.Budget Circuit Breaker: 워크플로우당 최대 실행 단계(Step) 50회, 최대 LLM 비용 $2.00 도달 시 강제 종료됩니다.6.2 Secrets ManagementAPI Key(OpenAI, EODHD 등)는 절대 DB나 코드에 평문으로 저장되지 않습니다.HashiCorp Vault 또는 Docker Secrets를 통해서만 런타임에 환경변수로 주입됩니다.7. Execution Metrics (성공 기준)일정(Timeline)이 아닌 기술적 성능(Performance)을 기준으로 합니다.Latency (반응 속도):Intent Parsing: < 2.0s (P95)Graph Compilation: < 1.0s (P95)Reliability (신뢰성):Graph Validation Pass Rate: > 95% (생성된 그래프가 문법적으로 실행 가능할 확률)Recovery Success Rate: 100% (서버 재시작 후 중단된 지점에서 재개 보장)Usability (사용성):"Time-to-First-Workflow": 신규 사용자가 설치 후 10분 이내에 첫 번째 자동화 성공.Appendix: Technical Decision Log (ADR)Decision: LangChain AgentExecutor 대신 LangGraph 사용.Reason: AgentExecutor는 블랙박스이며 커스터마이징이 어렵습니다. Human-in-the-Loop과 세밀한 상태 제어를 위해 LangGraph가 필수적입니다.Decision: Vector DB 별도 구축 대신 PostgreSQL (pgvector) 사용.Reason: 관리 포인트를 최소화합니다. 초기 Agent Registry 규모(수천 개 이하)에서는 pgvector 성능으로 충분합니다.
# TECH_SPEC.md — AgentForge

**버전**: 5.0  
**작성일**: 2025-12-03  
**상태**: Vision Document (Pre-Development)  
**Workflow Engine**: LangGraph

---

## 1. Vision (비전)

### 1.1 Why — 왜 만드는가

**문제 정의**:

전문가들은 수십 년간 축적한 **암묵지(Tacit Knowledge)**를 가지고 있다. 트레이더의 투자 판단 기준, 변호사의 계약서 검토 체크리스트, 연구자의 논문 스크리닝 방법론. 이 지식은 그들의 머릿속에만 존재하며, **"설명"할 수는 있지만 "코드화"할 수는 없다**.

기존 자동화 도구들은 이 문제를 해결하지 못한다:

| 도구 | 한계 |
|------|------|
| n8n/Zapier | "비개발자용"이라 하지만 트리거, 조건, 루프 등 프로그래밍적 사고 필요 |
| LangChain/LangGraph | 개발자 전용. 코드 없이는 불가능 |
| Dify/Flowise | 드래그 앤 드롭이지만 결국 "시각적 프로그래밍" |
| ChatGPT | 일회성 대화. 복잡한 워크플로우 불가능, 재사용 불가 |

**핵심 인사이트**:

> 전문가는 자신의 업무를 **"대화로 설명"**할 수 있다.  
> 우리는 그 대화를 **실행 가능한 Agent 팀**으로 변환한다.

### 1.2 What — 무엇을 만드는가

**AgentForge**는 대화형 AI Agent 생성 플랫폼이다.

```
입력: 전문가의 자연어 설명
     "매일 아침 9시에 거래량 상위 20개 종목 중
      RSI 30 이하면서 거래량 평균 2배 이상인 걸 찾아서
      뉴스 악재 없고 부채비율 200% 이하인 것만 골라
      총 자산 10% 이내로 분산 매수해줘"

출력: 실행 가능한 Agent 워크플로우
     [MarketDataAgent] → [TechnicalAnalyzer] → [NewsFilter] 
                      → [FundamentalChecker] → [RiskManager] → [Executor]
```

### 1.3 Core Principles — 핵심 원칙 (나침반)

모든 설계 결정은 이 5가지 원칙을 기준으로 판단한다:

| # | 원칙 | 의미 | 검증 질문 |
|---|------|------|----------|
| 1 | **Zero Programming** | 코드, 노드, API 몰라도 됨 | "코딩 모르는 사람이 혼자 할 수 있나?" |
| 2 | **Domain Language First** | 전문 용어 그대로 사용 | "사용자가 자기 언어로 말하고 있나?" |
| 3 | **Progressive Clarification** | AI가 불명확한 부분을 질문 | "시스템이 먼저 물어보고 있나?" |
| 4 | **Explainable Execution** | 실행 과정을 자연어로 설명 | "지금 뭐 하는지 이해할 수 있나?" |
| 5 | **Iterative Refinement** | 실행 후 대화로 수정 | "결과 보고 바로 고칠 수 있나?" |

### 1.4 What We Are NOT — 안티 패턴

명확한 경계 설정:

| 우리는 | 우리는 아니다 |
|--------|--------------|
| 대화로 Agent를 만드는 플랫폼 | 또 하나의 No-Code 빌더 |
| 비개발자를 위한 도구 | 개발자 생산성 도구 |
| 도메인 전문가의 암묵지 자동화 | 범용 챗봇 |
| Agent 팀 오케스트레이션 | 단일 Agent 실행기 |
| Self-Hosted 우선 | SaaS Only |

### 1.5 Success Definition — 성공의 정의

**Phase 1 성공 기준** (MVP):

- 코딩 경험 없는 사용자가 **10분 내** 첫 워크플로우 생성
- 설치부터 첫 실행까지 **5분 이내** (Docker)
- 투자 도메인 시나리오 **1개 완전 동작**

**Ultimate Vision** (2027):

```
"모든 전문가가 자신만의 AI 팀을 가진다"

- 투자자: 24시간 자동 모니터링 & 매매 Agent 팀
- 변호사: 계약서 검토 & 리스크 플래깅 Agent 팀  
- 연구자: 논문 수집 & 요약 & 트렌드 분석 Agent 팀
- 크리에이터: 기획 → 제작 → 배포 전체 자동화 Agent 팀
```

### 1.6 Evolution Roadmap — 진화 방향

```
2025 Q1: "대화로 Agent 만들기"
         └── 사용자 설명 → Agent 팀 자동 구성

2025 Q3: "Agent가 Agent 만들기"  
         └── 필요한 기능 없으면 Meta-Agent가 생성

2026: "Agent가 스스로 진화하기"
      └── 사용 패턴 학습 → 자동 개선 → A/B 테스트

2027: "모든 작업에 최적 Agent 자동 존재"
      └── 커뮤니티 공유 → 포크 → 병합 → 집단 지성
```

---

## 2. System Architecture (시스템 아키텍처)

### 2.1 4-Layer Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Conversation Interface                            │
│  ─────────────────────────────────────────────────────────  │
│  • WebSocket 기반 실시간 채팅                                │
│  • Progressive Q&A Flow                                     │
│  • 워크플로우 시각화 (React Flow)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Intelligence Core                                 │
│  ─────────────────────────────────────────────────────────  │
│  • Intent Parser (도메인 분류, 목표 추출, 작업 분해)          │
│  • Agent Matchmaking (요구사항 → Agent 매칭)                 │
│  • Workflow Synthesizer (Agent 조합 → 실행 그래프)           │
│  • Execution Explainer (실행 상황 자연어 설명)               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2.5: Meta-Agent Layer (Phase 4)                      │
│  ─────────────────────────────────────────────────────────  │
│  • Capability Gap Detection                                 │
│  • Agent Auto-Generation                                    │
│  • Continuous Learning Engine                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: Execution Runtime                                 │
│  ─────────────────────────────────────────────────────────  │
│  • LangGraph (워크플로우 실행 엔진)                          │
│  • Agent Sandbox (Docker 격리 실행)                         │
│  • NATS JetStream (이벤트 버스)                             │
│  • External Service Connectors                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Technology Stack

| Layer | Technology | 선택 이유 |
|-------|------------|----------|
| **Frontend** | Next.js 14, TypeScript | App Router, Server Components |
| | Shadcn/UI + TailwindCSS | 빠른 UI 개발, 커스터마이징 용이 |
| | React Flow | 워크플로우 시각화 |
| | Zustand | 경량 상태 관리 |
| **Backend** | FastAPI (Python 3.11+) | 비동기 네이티브, 타입 힌트 |
| | Pydantic v2 | 스키마 검증, LLM 구조화 출력 |
| | **LangGraph** | 워크플로우 실행, Human-in-the-Loop |
| **Messaging** | NATS JetStream | 이벤트 스트리밍, At-least-once 보장 |
| | Redis | 세션 캐시, Rate Limiting, 분산 락 |
| **Storage** | PostgreSQL | 주 데이터베이스 |
| | SQLite | 개발/소규모 배포 옵션 |
| **Infra** | Docker | Agent 샌드박스, 배포 |
| | HashiCorp Vault | 시크릿 관리 |

### 2.3 NATS vs Redis 역할 분리

```yaml
NATS JetStream:
  역할: 이벤트 기반 통신
  사용처:
    - Agent 간 실시간 메시지 전달
    - Workflow 실행 이벤트 스트리밍
    - 승인 요청/응답 비동기 처리
    - Worker 작업 분배

Redis:
  역할: 캐싱 및 상태 관리
  사용처:
    - WebSocket 세션 캐시
    - API Rate Limiting
    - 임시 실행 결과
    - 분산 락 (Redlock)
```

---

## 3. Core Components (핵심 컴포넌트)

### 3.1 Conversation Layer

**역할**: 사용자와의 자연어 인터페이스

**핵심 기능**:
- WebSocket 기반 실시간 양방향 통신
- 대화 컨텍스트 유지 (세션 관리)
- Progressive Clarification 질문 렌더링
- 워크플로우 실행 상태 실시간 표시

**데이터 흐름**:
```
User Message → WebSocket → Conversation Manager 
            → Intent Parser → Response/Question
            → WebSocket → User
```

### 3.2 Intent Parser

**역할**: 자연어를 구조화된 Intent로 변환

**처리 파이프라인**:

| Stage | 입력 | 출력 | 예시 |
|-------|------|------|------|
| 1. Domain Classification | 사용자 메시지 | 도메인 | "투자", "법률", "연구" |
| 2. Goal Extraction | 메시지 + 도메인 | 목표 | "자동 매매", "계약서 검토" |
| 3. Task Decomposition | 목표 | 작업 리스트 | ["데이터 수집", "분석", "실행"] |
| 4. Constraint Detection | 메시지 | 제약 조건 | "한국 주식만", "리스크 5% 이내" |
| 5. Ambiguity Detection | 작업 + 제약 | 불명확 요소 | ["데이터 소스?", "분석 기준?"] |

**출력 스키마**:
```
Intent:
  domain: string
  goal: string
  tasks: Task[]
  constraints: Constraint[]
  missing_info: string[]        # → Progressive Clarification 질문으로 변환
  confidence: float
```

### 3.3 Agent Registry & Matchmaking

**Agent Registry**:
- 사용 가능한 Agent 목록 관리
- Agent 메타데이터 (capabilities, inputs, outputs)
- 버전 관리 및 의존성 추적

**Agent 메타데이터 구조**:
```
Agent:
  id: string
  name: string
  description: string           # 자연어 설명 (매칭에 사용)
  domain: string[]              # 적용 가능 도메인
  capabilities: string[]        # 제공 기능 태그
  inputs: Schema                # 필요 입력
  outputs: Schema               # 출력 형태
  config_schema: Schema         # 설정 옵션
  requires_approval: boolean    # Human-in-the-Loop 필요 여부
```

**Matchmaking Algorithm**:
```
1. Domain Filter: intent.domain과 일치하는 Agent 필터링
2. Capability Match: intent.tasks와 agent.capabilities 매칭
3. Dependency Resolution: 필요 입력/출력 체인 구성
4. Gap Detection: 매칭되지 않는 task 식별 → Meta-Agent 또는 사용자 질문
```

### 3.4 LangGraph Workflow Engine

**역할**: Agent 조합을 실행 가능한 그래프로 변환하고 실행

**LangGraph 선택 이유**:

| 요구사항 | LangGraph 지원 |
|---------|---------------|
| 조건부 분기 | `add_conditional_edges()` |
| Human-in-the-Loop | `interrupt()` + `Command(resume=...)` |
| 상태 관리 | `TypedDict` 기반 State |
| 스트리밍 | `astream()` with `stream_mode` |
| 체크포인트 | `MemorySaver`, `PostgresSaver` |
| 서브그래프 | 중첩 그래프 지원 |

**Workflow State 구조**:
```
WorkflowState:
  # 실행 컨텍스트
  workflow_id: string
  current_node: string
  
  # 데이터 흐름
  inputs: dict                  # 초기 입력
  outputs: dict                 # 누적 출력
  
  # Human-in-the-Loop
  pending_approval: ApprovalRequest | None
  approval_result: ApprovalResult | None
  
  # 메타데이터
  started_at: datetime
  messages: list                # 실행 로그
```

**핵심 노드 타입**:

| 노드 타입 | 역할 | LangGraph 구현 |
|----------|------|---------------|
| AgentNode | Agent 실행 | 일반 함수 노드 |
| ConditionNode | 조건 분기 | `add_conditional_edges()` |
| ApprovalNode | 승인 대기 | `interrupt()` 사용 |
| ParallelNode | 병렬 실행 | `Send()` API |

**이벤트 스트리밍**:
```
LangGraph astream() → NATS Publish → WebSocket → Frontend

이벤트 타입:
- node_start: 노드 실행 시작
- node_complete: 노드 실행 완료
- approval_request: 승인 요청
- workflow_complete: 전체 완료
- error: 에러 발생
```

### 3.5 Meta-Agent System (Phase 4)

**역할**: 시스템 자가 진화

**핵심 기능**:

| 기능 | 설명 |
|------|------|
| Capability Gap Detection | 요청된 기능 중 기존 Agent로 처리 불가능한 것 탐지 |
| Agent Specification | Gap에 대한 Agent 설계서 자동 생성 |
| Code Generation | 설계서 기반 Agent 코드 생성 |
| Safety Validation | 생성된 코드 안전성 검증 |
| Sandbox Testing | 격리 환경에서 테스트 실행 |
| Registry Integration | 검증 통과 시 Agent Registry 등록 |

**진화 사이클**:
```
사용자 요청 → Gap 탐지 → Agent 설계 → 코드 생성 → 안전성 검증
                                                    ↓
Registry 등록 ← 테스트 통과 ← 샌드박스 테스트 ← 코드 검토
```

---

## 4. Data Models (데이터 모델)

### 4.1 Core Entities

**Conversation**:
```
id: UUID
user_id: UUID
created_at: datetime
updated_at: datetime
status: enum [active, completed, abandoned]
context: JSON                   # 대화 컨텍스트
```

**Intent**:
```
id: UUID
conversation_id: UUID
domain: string
goal: string
tasks: JSON[]
constraints: JSON[]
missing_info: string[]
confidence: float
created_at: datetime
```

**Workflow**:
```
id: UUID
intent_id: UUID
name: string
description: string
graph_definition: JSON          # LangGraph 직렬화
status: enum [draft, ready, running, completed, failed]
created_at: datetime
updated_at: datetime
```

**Agent**:
```
id: UUID
name: string (unique)
version: string
description: string
domain: string[]
capabilities: string[]
input_schema: JSON
output_schema: JSON
config_schema: JSON
code_hash: string               # 코드 무결성 검증
is_system: boolean              # 시스템 제공 vs 사용자 생성
created_at: datetime
```

**Execution**:
```
id: UUID
workflow_id: UUID
status: enum [pending, running, paused, completed, failed, cancelled]
state: JSON                     # LangGraph 체크포인트
started_at: datetime
completed_at: datetime
error: JSON | null
```

### 4.2 Database Schema Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│conversations│────<│   intents   │────<│  workflows  │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
                    ┌─────────────┐     ┌──────┴──────┐
                    │   agents    │>────│ executions  │
                    └─────────────┘     └─────────────┘
                           │
                    ┌──────┴──────┐
                    │workflow_nodes│ (Agent 사용 관계)
                    └─────────────┘
```

---

## 5. Integration Points (통합 지점)

### 5.1 LLM Provider Interface

**계층화된 라우팅**:

| Tier | 작업 | 권장 모델 | Latency 목표 |
|------|------|----------|-------------|
| Lightweight | Intent 분류, 실행 설명, 간단한 Q&A | Ollama 8B, Claude Haiku | < 500ms |
| Heavyweight | 코드 생성, 복잡한 워크플로우, Progressive Clarification | Claude Sonnet, GPT-4o | < 5s |

**Provider 추상화**:
```
LLMProvider (Interface):
  - complete(prompt) → string
  - complete_structured(prompt, schema) → BaseModel
  
구현체:
  - ClaudeProvider
  - OpenAIProvider  
  - OllamaProvider
  - AzureOpenAIProvider
```

### 5.2 External Service Connectors

**Connector 구조**:
```
Connector:
  id: string
  name: string
  auth_type: enum [api_key, oauth2, basic]
  base_url: string
  rate_limit: RateLimitConfig
  
ConnectorInstance:
  connector_id: string
  credentials: VaultReference    # Vault 참조, 직접 저장 안함
  user_id: UUID
```

**초기 지원 Connector (MVP)**:
- EODHD (주식 데이터)
- News API
- Slack (알림)
- Email (SMTP)

### 5.3 Event Flow (NATS)

**Topic 구조**:
```
agentforge.workflow.{workflow_id}.events.{event_type}

event_type:
  - started
  - node.started
  - node.completed
  - approval.requested
  - approval.received
  - completed
  - failed
```

---

## 6. Deployment Strategy (배포 전략)

### 6.1 Deployment Models

| 모델 | 대상 | 특징 |
|------|------|------|
| **Self-Hosted (Docker)** | 개인, 스타트업 | 5분 내 시작, SQLite 옵션, 완전 오프라인 가능 |
| **Self-Hosted (K8s)** | 기업 | 수평 확장, HA 구성 |
| **Cloud (향후)** | SaaS | 관리형 서비스 |
| **Hybrid** | 대기업 | 민감 데이터 내부, 나머지 클라우드 |

### 6.2 Docker Compose (MVP)

**구성 요소**:
```yaml
services:
  agentforge:        # API 서버 + Worker
  frontend:          # Next.js
  postgres:          # 또는 SQLite volume
  redis:             # 캐시
  nats:              # 이벤트 버스
```

**목표**: `docker compose up` 한 번으로 전체 실행

### 6.3 LLM 전략

| 환경 | 권장 구성 | 특징 |
|------|----------|------|
| 개발/테스트 | Ollama (로컬) | 무료, 오프라인 |
| 스타트업 | Claude API | 고성능, 종량제 |
| 기업 (일반) | Azure OpenAI | 엔터프라이즈 지원 |
| 기업 (보안) | vLLM + 로컬 70B | 완전 격리 |
| Air-gapped | Ollama 전용 | 외부 연결 없음 |

---

## 7. Security & Safety (보안)

### 7.1 Agent Sandbox

**격리 수준**:
- Docker 컨테이너 기반 실행
- 리소스 제한 (CPU, Memory, 실행 시간)
- 네트워크 화이트리스트 (허용된 호스트만 접근)
- Read-only 파일시스템 + tmpfs

### 7.2 Code Generation Safety (Phase 4)

**검증 체크리스트**:
- [ ] 허용된 import만 사용
- [ ] 금지된 함수 호출 없음 (exec, eval, subprocess 등)
- [ ] 네트워크 접근 범위 제한
- [ ] 파일시스템 접근 제한
- [ ] 무한 루프 / 리소스 고갈 패턴 없음

### 7.3 Secrets Management

- 모든 API 키, 자격 증명은 HashiCorp Vault 저장
- Agent 코드에 직접 노출 안함
- 런타임에 주입, 로그에 마스킹

---

## 8. Observability (관측성)

### 8.1 Logging

**구조화 로깅 (structlog)**:
```
필수 필드:
  - timestamp
  - level
  - workflow_id
  - node_id (해당시)
  - event
  - duration_ms (해당시)
```

### 8.2 Metrics (Prometheus)

**핵심 메트릭**:
- `workflow_executions_total` (status별)
- `workflow_duration_seconds` (histogram)
- `agent_executions_total` (agent별, status별)
- `llm_requests_total` (provider별)
- `llm_latency_seconds` (histogram)

### 8.3 Tracing (OpenTelemetry)

**Span 구조**:
```
Workflow Execution
  └── Node: MarketDataAgent
      └── LLM Call
      └── External API Call
  └── Node: TechnicalAnalyzer
      └── LLM Call
  └── Node: ApprovalGate
      └── Wait for Approval
```

---

## 9. Success Metrics (성공 지표)

### 9.1 User Experience

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| Time-to-First-Run | < 5분 | Docker 시작 ~ 브라우저 접속 |
| Time-to-First-Workflow | < 10분 | 접속 ~ 첫 워크플로우 생성 |
| Configuration Completion Rate | > 80% | 설정 시작 대비 완료 비율 |

### 9.2 System Performance

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| Intent Parsing Latency | < 2s | P95 |
| Workflow Compilation | < 1s | P95 |
| Agent Matching Accuracy | > 90% | 샘플 검증 |
| Execution Error Rate | < 5% | 실패 / 전체 실행 |

### 9.3 Self-Evolution (Phase 4)

| 지표 | 목표 | 측정 방법 |
|------|------|----------|
| Auto-Generated Agents | 월 50개+ | Registry 신규 등록 |
| Generated Agent Quality | > 4.0/5.0 | 사용자 평점 |
| Evolution Success Rate | > 60% | 개선 제안 → 실제 적용 |

---

## 10. Appendix

### 10.1 용어집

| 용어 | 정의 |
|------|------|
| Agent | 특정 작업을 수행하는 독립 실행 단위 |
| Workflow | Agent들의 실행 순서와 데이터 흐름을 정의한 그래프 |
| Intent | 사용자 요청을 구조화한 중간 표현 |
| Progressive Clarification | 불명확한 요소를 대화로 구체화하는 과정 |
| Meta-Agent | 다른 Agent를 생성/개선하는 Agent |
| Human-in-the-Loop | 실행 중 사람의 승인/개입이 필요한 지점 |

### 10.2 xflow-engine → LangGraph 매핑

| xflow-engine | LangGraph | 비고 |
|--------------|-----------|------|
| `XFlowTask` | 함수 노드 | `@node` 또는 일반 함수 |
| `XFlowCondition` | `add_conditional_edges()` | 조건부 라우팅 |
| `XFlowApproval` | `interrupt()` | Human-in-the-Loop |
| `Message` 스트리밍 | `astream(stream_mode="updates")` | 이벤트 스트리밍 |
| `XFlowSpec` | `StateGraph` | 그래프 정의 |
| Context | `TypedDict` State | 상태 관리 |

### 10.3 Phase 구분

| Phase | 기간 | 핵심 목표 | 주요 산출물 |
|-------|------|----------|------------|
| **0** | 2주 | 방향 검증 | Hardcoded Demo, 피드백 수집 |
| **1** | 6주 | MVP | 투자 도메인 1개 시나리오 동작 |
| **2** | 8주 | 확장 | 다중 도메인, Human-in-the-Loop |
| **3** | 10주 | Production | 보안, 스케일링, 모니터링 |
| **4** | 12주 | Self-Evolution | Meta-Agent, Marketplace |

---

**문서 버전**: 5.0  
**최종 수정**: 2025-12-03  
**다음 단계**: 이 문서 기반으로 Phase별 상세 Plan 수립
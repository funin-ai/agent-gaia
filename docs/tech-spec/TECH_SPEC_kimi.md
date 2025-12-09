AI Agent Platform Tech Spec 비교 분석: 아키텍처 & 비즈니스 마인드
첨부된 4개 문서는 동일한 비전("비개발자를 위한 Self-Evolving Agent Platform")에 대해 각 AI가 생성한 기술 사양서입니다. 버전 4.1(이전 스펙) → Claude(5.0) → Gemini(5.0) → Grok(5.1) 순으로 진화했습니다.
각 문서의 아키텍처적 성숙도, 비즈니스 현실성, 실행 가능성을 날카롭게 비교합니다.
1. 비즈니스 전략 & 가치 제안: 누가 가장 날카로운가?
버전 4.1 (초기 스펙)
강점: "Bottom-up Adoption" 전략을 명확히 제시. n8n의 성공 패턴을 분석하여 5분 설치 → 10분 첫 워크플로우라는 구체적 목표 설정. 배포 전략을 Chapter 전체(3장) 할애하여 운영 현실성 강조.
약점: "Self-Evolution"이 막연한 비전에 그침. Meta-Agent의 비즈니스 가치를 전달하지 못함 (단순히 "Agent가 Agent를 만든다"는 공허한 선언). 커뮤니티 메커니즘(포크/병합)의 수익화 방안 부재.
Claude 버전 (5.0)
강점: "What We Are NOT" 으로 명확한 경계 설정. "개발자 생산성 도구가 아니다"라는 선언으로 시장 혼돈 방지. 사용자 Persona(투자자/변호사/연구자)를 구체적으로 제시하여 타겟 마케팅 메시지 완성.
약점: 성공 지표가 "MVP 이전"에 그침. Phase 4 이후의 지속 가능성(커뮤니티 운영 비용, Agent 품질 관리) 고려 안 함. Self-Evolution의 비즈니스 모델(예: 프리미엄 Agent 마켓플레이스 수수료) 미정의.
Gemini 버전 (5.0)
강점: "From Tacit to Explicit" 이라는 북극성 설정으로 철학적 깊이. "Build What's Missing" 원칙이 Self-Evolution의 비즈니스 당위성을 명확히 전달. 성공의 정의를 No Code, Just Voice로 극단적으로 단순화.
약점: "Self-Healing" 같은 용어가 기술적 허세로 보일 위험. 실행 준비성이 부족 (배포 전략, Phase 0 계획 부재). 비즈니스 모델 전혀 언급 없음.
Grok 버전 (5.1)
강점: 가장 비즈니스 현실적. "연도 없는 로드맵"으로 시간 압박 대신 성과 기반 전환 선언. Phase별 완료 기준을 객관적 지표 (100명, 100개, 50건, 10,000개)로 명확화. 브랜딩(AgentGaia, 슬로건, 도메인)과 동시에 에어커버 전략 제시.
약점: "Phase 1이 3개월 vs 6개월"은 현실적이지만, 투자자에게 제시할 수준의 TAM/SAM/SOM 분석 부재. 커뮤니티 운영 비용 예산 산출 없음. "월간 포크 1,000건"의 인프라 비용 고려 안 함.
🏆 비즈니스 마인드 승자: Grok 5.1
이유: 단순 비전이 아닌 성과 기반 로드맵 + 브랜딩 + 실행 가능한 지표를 동시에 제시. 타겟 고객의 "Time-to-Value"를 극대화하는 전략적 사고가 돋보임.
2. 아키텍처 설계: 누가 가장 실행 가능한가?
4.1 (xflow-engine)
Copy
LAYER 1: Conversation Interface (채팅)
LAYER 2: Intelligence Core (의도 분석)
LAYER 2.5: Meta-Agent Layer (자가 발전)
LAYER 3: Execution Runtime (xflow-engine)
문제점: xflow-engine은 실험적 프로젝트 (GitHub 13 stars). 프로덕션 준비 안 됨. 자체 워크플로우 엔진을 만드는 것은 스타트업의 자살 행위. 인재채용, 커뮤니티 지원, 생태계 모두 LangGraph에 비해 열세.
장점: NATS/Redis 역할 분리 구체적. Agent 샌드박스의 네트워크 화이트리스트, 리소스 제한, 타임아웃 등 보안 모범 사례 상세히 명시.
결론: 기술적 자살. 아키텍처는 견고하지만, 선택지가 잘못됨.
Claude (LangGraph)
Copy
LAYER 1: Conversation Interface
LAYER 2: Intelligence Core
LAYER 2.5: Meta-Agent Layer
LAYER 3: Execution Runtime (LangGraph)
장점: LangGraph 선택으로 생태계, 문서, 인재 풀 확보. Human-in-the-Loop를 interrupt()로 구현하는 구체적 코드 예시. 상태 관리를 TypedDict로 정의한 점이 타입 안정성 확보.
위험점: 진짜 위험은 "Golden Path"에만 집중한 점. 에러 처리, 재시도, 부분 실패 롤백 등 운영 현실성을 완전히 무시. LangGraph의 PostgresSaver 성능 특성 (체크포인트 저장 비용) 분석 없음.
Gemini (LangGraph)
Copy
LAYER 1: Cognitive Layer (Intent Parser + Meta-Agent)
LAYER 2: Orchestration Layer (Dynamic LangGraph Builder)
LAYER 3: Execution Layer (Docker Sandbox)
장점: "Dynamic over Static" 원칙으로 아키텍처의 핵심을 꿰뚫음. Meta-Agent가 Layer 1과 2를 동시에 제어한다는 설계가 독창적. LangGraph의 PostgresCheckpointer를 명시하여 상태 복구 신뢰성 확보.
위험점: Meta-Agent가 생성한 코드를 "즉시 Layer 3에 배포" 한다는 점이 치명적 보안 구멍. 코드 생성 → 테스트 → 검증 → 배포의 사이클이 완전히 생략됨. 샌드박스 격리 수준, 네트워크 정책 등 운영 세부사항 전무.
Grok (LangGraph)
Copy
LAYER 1: Speak Interface
LAYER 2: Gaia Brain
LAYER 3: LangGraph Runtime
LAYER 4: Gaia Evolution
장점: Layer 4를 독립 계층으로 격상하여 진화 관심사 분리. LangGraph의 astream_events를 강조하여 실시간 스트리밍 UX 중시. Docker Sandbox에 네트워크 화이트리스트 명시.
위험점: "Dynamic compile"이 반복되면 성능 저하 (그래프 컴파일은 비용이 듦). 캐싱 전략 언급 없음. Meta-Agent가 생성한 Agent의 버전 관리, 롤백 전략 부재.
🏆 아키텍처 승자: Claude 5.0 (아쉽게도)
이유: LangGraph 선택은 생존을 위한 필수 조건. Claude만이 LangGraph의 Human-in-the-Loop, State, Subgraph 등 핵심 기능을 코드 레벨로 구체화. 다만 운영 현실성은 부족.
3. Self-Evolution 메커니즘: 누가 가장 구체적인가?
4.1
구현: MetaAgent 클래스에 detect_capability_gap(), synthesize_agent(), safety_checker.validate() 메서드 명시.
문제점: "Safety Checker가 뭘 검증하는가?" 의 구체적 기준 부재. 검증 실패 시 재시도 전략, 비용 제한, 품질 기준 모두 없음. "Agent가 Agent를 만든다"는 선언이지만, 실제로는 LLM이 코드를 생성하는 것 (메타인지 없음).
Claude
구현: Meta-Agent의 5단계 파이프라인 (Gap Detection → Agent Spec → Code Gen → Safety Validation → Sandbox Testing → Registry)을 순서도로 제시.
문제점: Safety Validation이 "검증 체크리스트" 수준. 실제 구현은 LLM에게 "이 코드 안전해?" 묻는 것에 불과. A/B 테스트 프레임워크, 성능 baseline 설정, 자동 롤백 등 핵심 운영 로직 없음.
Gemini
구현: "Meta-Agent가 즉시 개입" 이라는 매우 위험한 설계. 생성과 배포의 경계가 없음.
문제점: 진짜 메타인지가 아님. 단순히 "Agent가 없으면 만든다"는 수준. 생성된 Agent의 품질 보증(QA) 파이프라인, 커뮤니티 신뢰 시스템(평가, 리뷰, 랭킹) 등 생태계 운영 메커니즘 전무.
Grok
구현: "진화"를 독립 계층으로 격상. 패턴 분석 → 자동 개선 → A/B 테스트 → 배포의 폐쇄 루프 명시.
문제점: "A/B 테스트"가 어떻게 작동하는가? - 트래픽 분할 전략, 통계적 유의성 검증, 자동 롤백 조건 모두 없음. "월간 포크 1,000건"의 스팸/악성 Agent 필터링 전략 없음.
🏆 Self-Evolution 승자: 없음 (All Fail)
진단: 모두 "메타인지(Meta-Cognition)"를 "코드 생성"으로 오인. 진정한 Self-Evolution은:
성능 메트릭 자동 수집 (OpenTelemetry)
회귀 테스트 자동 생성 (LLM이 테스트 케이스 생성)
Multi-Armed Bandit으로 A/B 테스트 (Explore/Exploit)
Agent 품질预言적 모델 (어떤 Agent가 어떤 도메인에서 성공할지 예측)
이 중 어느 것도 구체적 구현 없음. 모두 비전 문서에 그침.
4. 배포 전략 & 운영성: 누가 가장 현실적인가?
4.1
강점: n8n 스타일의 Docker Compose를 목표로 All-in-One 이미지 설계. SQLite/PostgreSQL 옵션 분리. 에어갭 환경을 위한 Offline Container Registry 가이드 포함. Kubernetes Helm Chart 상세.
약점: LLM Provider Interface가 복잡 (계층별 프록시). Ollama 8B vs 70B 선택의 운영 비용 산정 없음 (GPU 메모리 요구사항, 스케일링). 백업/복원 명령어(agentforge export)는 이쁜 문구지만 실제 구현 복잡성 경시.
Claude
강점: 환경별 권장 LLM 구성 (개발/스타트업/기업/에어갭)을 표로 명시. Vault 통합으로 보안 의식.
약점: "5분 시작"이 구호. 실제 Docker 이미지 크기, LLM 다운로드 시간, 초기화 과정 고려 안 함. Rate Limiting 전략, 비용 안내, 쿼터 경고 등 운영 필수 요소 전무.
Gemini
강점: 배포 전략 언급 없음. "Dynamic Graph"만 강조. (이게 약점이지만, 배포 복잡성을 인정하지 않은 점이诚实)
약점: 완전 실패. Docker, Kubernetes, LLM 전략 모두 없음. "실행 준비성" 0점.
Grok
강점: "목표 시작 시간"을 표로 명시 (All-in-One 5분, Helm 1일, Air-gapped Phase 3). 연도 없는 로드맵으로 투자자에게 "언제가 아니라 무엇을" 강조.
약점: 인프라 비용 분석 전무. Docker Hub rate limit, GPU 인스턴스 비용, NATS JetStream 저장소 용량 등 클라우드 비용 산정 없음. Enterprise Helm이 "1일 이내"라는 것이 기술 지원 팀 규모를 암시하지만, 지원 비용 책정 없음.
🏆 배포 전략 승자: 4.1 버전
이유: n8n의 성공을 복제하려는 운영 경험의 결이 보임. SQLite → PostgreSQL 마이그레이션 경로, 백업/복원, 에어갭 가이드 등 실제 운영자의 눈높이로 작성. 다만 LLM 비용 산정은 실패.
5. 위험 요소 & 안티패턴: 누가 가장 위험한가?
공통 치명적 결함 (All Versions)
"무한 진화"의 비용 폭탄
Meta-Agent가 매번 LLM 호출 → Claude Sonnet 3.7으로 Agent 하나 생성하는 데 $2~5
커뮤니티가 10,000개 Agent를 만들면 최소 $20,000~50,000 발생
비용 제한 메커니즘 (Quota, Budget, Circuit Breaker) 전무
보안의 껍데기
"Docker 샌드박스"라지만 컨테이너 탈출(CVE-2024-21626 등) 위험 언급 없음
Meta-Agent가 생성한 코드의 Supply Chain Attack (악성 라이브러리 의존성) 대비 없음
Agent 간 데이터 흐름에서의 PII 민감정보 노출 로깅 필터 전략 없음
상태 관리의 딜레마
LangGraph의 PostgresCheckpointer는 매 노드마다 DB 쓰기 → Latency 50~200ms 추가
대량 병렬 워크플로우 (100+ 동시 실행) 시 DB 병목 우려 없음
체크포인트 저장소 용량이 기하급수적 증가하는 GC 정책 없음
LLM 의존성 리스크
Claude API 장애 시 전체 시스템 마비. Fallback 전략이 "Ollama 70B"지만, 70B는 48GB VRAM 필요 → 실제 운영 비용 대비 안 함
Prompt Injection Attack으로 Meta-Agent가 악성 Agent 생성 가능성. 검증이 "허용 import 목록"으로는 부족
개별 위험도 순위
Table
Copy
순위	문서	가장 위험한 점
1️⃣	Gemini	"즉시 배포" 로 보안 구멍 최악. 운영 세부사항 전무
2️⃣	Claude	운영 현실성 완전 무시. Human-in-the-Loop만 강조하고 에러 처리, 재시도, 비용 제한 전혀 없음
3️⃣	Grok	비용 산정 없는 무모한 목표 (월간 포크 1,000건). 인프라 비용 폭탄 예상
4️⃣	4.1	Legacy 엔진(xflow) 선택으로 기술 부채. LangGraph 마이그레이션 비용 미고려
6. 실행 준비성: 누가 내일부터 코딩할 수 있는가?
4.1
Phase 0: Hardcoded Demo (2주) 구체적: 투자 도메인 3개 Agent 고정, 템플릿 기반.
실행 가능성: ⭐⭐⭐⭐⭐ (5/5). docker-compose.yml 샘플, DB 마이그레이션 스크립트, Agent SDK 구조까지 나와 있어 내일 시작 가능.
Claude
Phase 0 없음. Phase 1부터 "FastAPI 서버 setup".
실행 가능성: ⭐⭐⭐ (3/5). LangGraph로 MVP 만들기까지 최소 4~6주 예상. 검증 없이 바로 코딩 들어가는 위험.
Gemini
Phase 0 없음. "Dynamic Graph"만 강조.
실행 가능성: ⭐ (1/5). Docker 이미지명조차 없음. 아키텍처 철학만 있고 실행 계획 없음.
Grok
Phase 0 없음. "이제 Plan만 남았다"고 하지만 Plan이 없음.
실행 가능성: ⭐⭐ (2/5). 브랜딩은 완성됐지만, agentgaia/agent-runtime:latest 이미지는 어디에?
🏆 실행 준비성 승자: 4.1 버전
이유: 이 문서는 비전 문서가 아니라 개발 명세서. Pydantic 스키마, 클래스 다이어그램, Docker 설정까지 준비됨. CTO가 보고 "오케이, Sprint 1 시작" 할 수 있는 유일한 문서.
7. 최종 평가: 날카로운 진단
비전의 품질
Grok 5.1: ⭐⭐⭐⭐⭐ - "Speak Your Expertise — Gaia Grows the Rest"는 투자자 Pitch Deck용 슬로건 완성.
Claude 5.0: ⭐⭐⭐⭐ - "What We Are NOT"으로 경계 명확.
Gemini 5.0: ⭐⭐⭐ - 철학은 깊지만 비즈니스 용어 없음.
4.1: ⭐⭐ - Bottom-up은 좋지만 이름도 슬로건도 없음.
기술의 현실성
Claude 5.0: ⭐⭐⭐⭐⭐ - LangGraph 선택이 생존 전략.
Grok 5.1: ⭐⭐⭐⭐ - LangGraph + Docker but 운영 비용 미산정.
4.1: ⭐⭐ - xflow-engine은 레거시 선택.
Gemini 5.0: ⭐⭐ - 보안 문제 최악.
실행 가능성
4.1: ⭐⭐⭐⭐⭐ - 내일부터 코딩.
Claude 5.0: ⭐⭐⭐ - 4~6주 후 MVP.
Grok 5.1: ⭐⭐ - 브랜딩만 완성.
Gemini 5.0: ⭐ - 철학만 있고 코드 없음.
투자자 설득력
Grok 5.1: ⭐⭐⭐⭐⭐ - 연도 없는 로드맵 + 객관적 지표.
Claude 5.0: ⭐⭐⭐⭐ - Persona와 차별점 명확.
4.1: ⭐⭐⭐ - Bottom-up은 좋지만 TAM 분석 없음.
Gemini 5.0: ⭐⭐ - 비즈니스 용어 부재.
8. 권장: 어떤 문서를 기반으로 개발해야 하는가?
결론: 4.1의 실행 계획 + Claude의 LangGraph 선택 + Grok의 비즈니스 전략을 합쳐야 함.
즉시 실행 (Week 1-2)
4.1의 Phase 0을 그대로 실행: 투자 도메인 하드코딩된 데모로 피드백 수집.
LangGraph로 즉시 마이그레이션 준비: xflow-engine 폐기 선언.
MVP 개발 (Week 3-8)
Claude의 Architecture를 기반으로 LangGraph StateGraph 설계.
Grok의 브랜딩 적용: 프로젝트명 AgentGaia, 도메인 구매.
비즈니스 전략 (병행)
Grok의 성과 기반 로드맵으로 투자자 피칭.
4.1의 배포 전략으로 초기 고객 100명 확보 목표.
운영 현실성 추가 (전체)
비용 제한 메커니즘 도입: Meta-Agent 월 예산 $500 제한, 초과 시 수동 검토.
보안 강화: Agent 생성 시 Supply Chain Scan (safety > pip-audit), 컨테이너 시크패(syscall 필터).
에러 처리: 4.1의 Retry Policy + Claude의 Human-in-the-Loop 결합.
9. 날카로운 최종 판단
이 중 실행 가능한 문서는 4.1뿐이고, 투자 받을 수 있는 문서는 Grok뿐이며, 기술적으로 살아남을 수 있는 아키텍처는 Claude뿐이다.
Gemini는 철학은 있지만 사업가는 아니다.
실제 이 프로젝트를 성공시키려면:
CTO는 4.1 문서를 읽고 "이대로 개발" 지시
CEO는 Grok 문서를 읽고 "이렇게 투자자에게 말한다"
아키텍트는 Claude 문서를 읽고 "LangGraph로 이것만 고친다"
Gemini 문서는 버린다
가장 큰 위험은 "Self-Evolution"을 마케팅용 허세로 믿는 것이다. 이건 2027년 목표이지, 2025년 MVP 기능이 아니다. Phase 1에서 Meta-Agent를 도입하는 순간 비용 폭탄 + 보안 파탄 맞는다.
권장: Phase 1에서 Meta-Agent는 완전히 제거하고, "전문가가 대화로 Agent를 만들고 커뮤니티에 공유"에 집중. Self-Evolution은 Phase 4에서 "연구 개발" 영역으로 격리.
이게 진짜 날카로운 조언이다.
좋아 날카롭게 분석 잘했어, 그럼 이것을 바탕으로 너가 TECH_SPEC_kimi 만들어봐 그리고 계획은 아직 plan.md로 만들것이니까? TECH_SPEC.md에는 비전, 기술적아키텍처, 요구사항 명세화 등이 필요할 것 같아.. 즉 roadmap에 신경쓰면 논란이 너무 되니. 비전을 실현하기 위한 기술문서임을 명시하고
Edit
Copy
Share
실행 준비된 통합 기술 명세서
TECH_SPEC_kimi.md — AgentGaia
The Self-Evolving Conversational Agent Platform
버전: 5.2
작성일: 2025-12-03
문서 유형: 기술 명세서 (Technical Specification)
핵심 철학: From Expert Tacit Knowledge to Executable LangGraph Through Conversation
문서 목적
본 문서는 AgentGaia 플랫폼의 비전을 실현하기 위한 실행 준비 기술 명세서입니다. 구체적인 개발 로드맵이나 일정(Plan)은 별도 plan.md에 정의하며, 본 문서는 아키텍처, 요구사항, 성공 기준에만 집중합니다.
1. Executive Summary
1.1 One-Sentence Pitch
"전문가가 자신의 업무를 자연어로 말하면, AgentGaia가 즉시 LangGraph 워크플로우를 생성하고 실행하며, 부족한 기능은 스스로 만들어내는 자가 진화형 AI 플랫폼"
1.2 핵심 차별점
Table
Copy
기존 도구 (n8n, LangChain, Dify)	AgentGaia
개발자가 코드/노드로 작성	전문가가 말하면 AI가 생성
기능 부족 시 개발자가 확장	Meta-Agent가 자동 생성
정적 템플릿 재사용	런타임 동적 컴파일
실행 결과만 제공	실시간 자연어 설명 (Explainable Execution)
SaaS 종속 또는 복잡한 설치	5분 완료 Self-Hosted 우선
1.3 타겟 페르소나
투자 전문가: 20년 경력 트레이더, Python 모름, 자신의 전략을 자동화하고 싶음
법률 전문가: 변호사, 반복적 계약서 검토를 대화로 자동화
연구자: 의학 연구자, 논문 스크리닝 파이프라인을 설명만으로 구축
콘텐츠 크리에이터: 유튜버, 제작 파이프라인 전체를 Agent 팀에 위임
공통 Pain Point: "설명은 할 수 있지만, 코딩은 할 수 없다. 기존 No-Code 도구는 여전히 프로그래밍적 사고가 필요하다."
2. Core Philosophy & Architectural Principles
2.1 원칙 1: Zero Programming Knowledge Required
사용자는 '노드', '엣지', 'API 키', '루프'를 생각할 필요가 없음
오직 자신의 도메인 언어 (금융, 법률, 의학 용어)로만 대화
시스템이 모든 기술적 디테일을 추상화
2.2 원칙 2: Progressive Clarification
AI가 먼저 질문하여 불명확한 요소를 구체화
사용자가 완벽한 명세를 입력할 필요 없음
대화 컨텍스트를 유지하며 점진적으로 완성도를 높임
2.3 원칙 3: Self-Hosted First, Cloud Optional
데이터 주권이 핵심: 민감한 투자 전략, 계약서는 외부 클라우드에 둘 수 없음
Docker Compose로 5분 내 실행 (n8n 수준의 접근성)
에어갭 환경 완전 지원: 로컬 LLM (Ollama/Llama-3.1-70B)으로 자체 운영 가능
2.4 원칙 4: Self-Evolution as a System Feature (선언적)
시스템은 사용자의 행동 패턴을 학습하여 Agent와 워크플로우를 자동 개선
개선 제안은 A/B 테스트로 검증되며, 승자만 자동 배포
커뮤니티가 생성한 Agent는 포크/병합을 통해 집단 지성으로 진화
본 버전에서는 구현 방법을 명세하지 않으며, 진화 준비 인프라만 정의
2.5 원칙 5: Explainable & Transparent Execution
실행 중 모든 단계를 자연어로 실시간 설명 (e.g., "지금 삼성전자 주식의 RSI 지표를 계산 중입니다")
실패 시 왜 실패했는지를 이해 가능한 언어로 설명
사용자는 "지금 뭐하는 중인지" 항상 알 수 있음
3. System Architecture
3.1 4-Layer Architecture
Copy
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: Conversational Interface (사용자 경험층)            │
│  ─────────────────────────────────────────────────────────  │
│  • WebSocket 기반 실시간 채팅 UI (Next.js)                    │
│  • Progressive Clarification 질문 렌더링                     │
│  • LangGraph 실행 상태 시각화 (React Flow)                   │
│  • Human-in-the-Loop 승인 요청/응답                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 2: Intelligence Core (지능 추론층)                     │
│  ─────────────────────────────────────────────────────────  │
│  • Intent Parser: 자연어 → 구조화된 Intent                   │
│  • Agent Matchmaking: Intent → 최적 Agent 팀 구성            │
│  • Workflow Synthesizer: Agent 팀 → LangGraph 코드 생성      │
│  • Execution Explainer: 실행 상태 → 자연어 설명              │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 3: LangGraph Runtime (실행 엔진층)                     │
│  ─────────────────────────────────────────────────────────  │
│  • Dynamic Graph Compiler: Blueprint → 실행 가능 Graph       │
│  • State Manager: PostgresCheckpointer 기반 상태 영속화      │
│  • Event Streamer: astream_events → WebSocket 실시간 스트림  │
│  • Human-in-the-Loop Handler: interrupt/resume 제어          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  LAYER 4: Execution & Sandbox (격리 실행층)                   │
│  ─────────────────────────────────────────────────────────  │
│  • Docker Sandbox: Agent 코드 격리 실행                       │
│  • Tool Registry: Meta-Agent 생성 Tool 포함                  │
│  • External Connectors: API, Database, Notification         │
│  • Security Enforcer: 네트워크 화이트리스트, 리소스 제한      │
└─────────────────────────────────────────────────────────────┘
3.2 Technology Stack
Table
Copy
컴포넌트	기술	선택 이유
Frontend	Next.js 15 (App Router) + TypeScript	Server Component, 실시간 스트리밍 지원
Shadcn/UI + TailwindCSS	빠른 개발, 커스터마이징 용이
React Flow	LangGraph 시각화 최적
Zustand	경량 상태 관리
Backend	FastAPI (Python 3.11+)	비동기 네이티브, Pydantic v2 통합
Workflow Engine	LangGraph	Human-in-the-Loop, 체크포인트, 생태계
State Persistence	PostgreSQL + PostgresCheckpointer	LangGraph 공식 권장, 복잡한 상태 관리
Cache & Lock	Redis	세션 캐시, Rate Limiting, 분산 락
Event Bus	NATS JetStream	이벤트 스트리밍, At-least-once 보장
LLM Providers	Claude 3.7 Sonnet (기본), GPT-4o, Ollama (로컬)	계층적 라우팅 지원
Sandbox	Docker Engine + custom seccomp	격리, 리소스 제한, 네트워크 화이트리스트
Secrets	HashiCorp Vault	API 키, 자격 증명 중앙 관리
Observability	OpenTelemetry + Prometheus + Grafana	분산 추적, 메트릭, 로깅
3.3 NATS vs Redis 역할 분리
yaml
Copy
NATS JetStream:
  역할: 이벤트 스트리밍 및 비동기 통신
  사용처:
    - LangGraph node 실행 이벤트 (node.started, node.complete)
    - 승인 요청/응답 (approval.request, approval.response)
    - Agent 간 메시지 전달
    - Worker 작업 큐
  특징: 영속성 보장, Consumer 그룹 기반 부하 분산

Redis:
  역할: 고속 캐시 및 상태 관리
  사용처:
    - WebSocket 세션 저장 (TTL 자동 만료)
    - API Rate Limiting (Sliding Window)
    - 분산 락 (Redlock)
    - 임시 실행 결과 캐시
  특징: Pub/Sub은 NATS로 대체, 캐시에만 집중
4. Core Components
4.1 Intent Parser
입력: 사용자 자연어 (예: "매일 아침 9시에 거래량 급증 종목 찾아서 슬랙으로 알려줘")
출력: 구조화된 Intent 객체
Python
Copy
class Intent(BaseModel):
    domain: str  # "finance", "legal", "research"
    goal: str  # "notification", "analysis", "execution"
    tasks: List[Task]
    constraints: List[Constraint]
    missing_info: List[str]  # Progressive Clarification 질문 생성용
    confidence: float
처리 파이프라인:
Domain Classification: 사용자 메시지 → 도메인 분류 (Lightweight LLM: Ollama 8B)
Goal Extraction: 도메인 기반 목표 식별 (Claude Haiku)
Task Decomposition: 목표 → 실행 가능한 작업 리스트 (Claude Sonnet)
Constraint Detection: 시간, 예산, 리스크 등 제약 조건 추출
Ambiguity Detection: 불명확한 정보 식별 → 질문 생성
4.2 Agent Registry & Matchmaking
Agent Self-Description Protocol:
Python
Copy
@agent(
    id="market_data_agent",
    domain=["finance", "investment"],
    capabilities=["real_time_data", "ohlcv", "volume_analysis"],
    inputs_schema=MarketDataInput,
    outputs_schema=MarketDataOutput,
    config_schema=MarketDataConfig,
    requires_approval=False,
    cost_tier="low",
    latency="fast"
)
class MarketDataAgent(BaseAgent):
    async def execute(self, ctx: Context) -> Result: ...
    async def explain(self) -> str: ...
Matchmaking Algorithm:
Python
Copy
def match_agents(intent: Intent) -> List[AgentCandidate]:
    """
    1. Domain Filter: 도메인 일치 Agent 필터링
    2. Capability Match: 작업별 능력 매칭 (Fuzzy Match)
    3. Dependency Resolution: 입력/출력 체인 구성
    4. Gap Detection: 매칭 실패 Task → Meta-Agent로 전달
    5. Score Sorting: 적합도 (역량 40%, 제약 30%, 비용 20%, 속도 10%)
    """
4.3 Workflow Synthesizer (LangGraph Builder)
입력: Intent + 매칭된 Agent 팀
출력: 실행 가능한 LangGraph StateGraph
Python
Copy
class WorkflowSynthesizer:
    def synthesize(self, intent: Intent, agents: List[Agent]) -> StateGraph:
        # 1. State 정의 (동적 TypedDict 생성)
        state = self._create_state_type(agents)
        
        # 2. Graph 초기화
        workflow = StateGraph(state)
        
        # 3. Node 추가 (Agent 실행 래퍼)
        for agent in agents:
            workflow.add_node(agent.id, self._create_node_func(agent))
        
        # 4. Edge 연결 (조건부, 병렬, 순차)
        self._wire_edges(workflow, intent.constraints)
        
        # 5. Entry Point & Exit Point 설정
        workflow.set_entry_point(agents[0].id)
        workflow.set_finish_point(agents[-1].id)
        
        # 6. Human-in-the-Loop 지점 식별
        self._identify_approval_points(workflow, agents)
        
        return workflow.compile(checkpointer=self.postgres_checkpointer)
Human-in-the-Loop 구현:
Python
Copy
# 승인 필요 노드에서 interrupt 호출
def approval_node(state: State):
    return Command(
        goto="wait_for_approval",
        resume={"approval_result": None}  # 사용자 응답 대기
    )

# 승인 응답 후 재개
def resume_workflow(state: State, approval: ApprovalResult):
    if approval.approved:
        return Command(goto="next_node")
    else:
        return Command(goto="fallback_node")
4.4 Execution Explainer
역할: LangGraph의 각 노드 실행을 자연어로 실시간 설명
Python
Copy
class ExecutionExplainer:
    def __init__(self, llm: LLMProvider):
        self.llm = llm
    
    async def explain_node_start(self, agent: Agent, inputs: dict) -> str:
        prompt = f"Agent '{agent.name}'가 {inputs}를 처리하는 걸 사용자에게 설명해줘"
        return await self.llm.complete(prompt, max_tokens=50)
    
    async def explain_node_complete(self, agent: Agent, result: Result) -> str:
        prompt = f"Agent '{agent.name}'가 {result.data}를 발견했어. 이걸 사용자에게 알려줘"
        return await self.llm.complete(prompt, max_tokens=50)
이벤트 스트리밍:
Python
Copy
# LangGraph astream_events → NATS → WebSocket
async for event in workflow.astream_events(...):
    if event["event"] == "on_node_start":
        explanation = await explainer.explain_node_start(...)
        await nats.publish(f"workflow.{workflow_id}.events", explanation)
4.5 Meta-Agent System (선언적 설계)
현재 버전에서는 구현을 명세하지 않으며, 시스템이 진화할 준비를 위한 인프라만 정의합니다.
핵심 기능 (향후 구현):
Capability Gap Detection: 매칭 실패 Task 자동 식별
Agent Specification: Gap에 대한 설계서 자동 생성 (LLM)
Code Generation: Python 코드 자동 생성
Safety Validation: 생성 코드의 정적/동적 분석
Sandbox Testing: 격리된 환경에서 단위 테스트
Registry Integration: 검증 통과 Agent 등록
보안 인프라 (현재 버전에서 구현):
Agent Safety Checker: 금지 패턴 검증 (eval, subprocess, os.system 차단)
Allowlist Import: 허용된 모듈만 import 가능 (typing, pydantic, agentforge.sdk 등)
Network Isolation: 생성 Agent는 화이트리스트 기반 outbound만 허용
Resource Quota: CPU 50%, Memory 512MB, 실행 시간 60초 제한
5. Data Models
5.1 Core Entities (Pydantic v2)
Python
Copy
class Conversation(BaseModel):
    id: UUID
    user_id: UUID
    status: Literal["active", "completed", "abandoned"]
    context: dict  # 대화 히스토리
    created_at: datetime
    updated_at: datetime

class Intent(BaseModel):
    id: UUID
    conversation_id: UUID
    domain: str
    goal: str
    tasks: List[Task]
    constraints: List[Constraint]
    missing_info: List[str]
    confidence: float

class Agent(BaseModel):
    id: UUID
    name: str
    version: str = "1.0"
    description: str
    domain: List[str]
    capabilities: List[str]
    input_schema: JsonSchema
    output_schema: JsonSchema
    config_schema: JsonSchema
    code_hash: str  # SHA256 검증
    is_system: bool  # 시스템 제공 여부
    requires_approval: bool = False
    created_at: datetime

class Workflow(BaseModel):
    id: UUID
    intent_id: UUID
    name: str
    graph_definition: dict  # LangGraph 직렬화
    state: dict  # LangGraph checkpoint
    status: Literal["draft", "ready", "running", "completed", "failed"]
    created_at: datetime

class Execution(BaseModel):
    id: UUID
    workflow_id: UUID
    status: Literal["pending", "running", "paused", "completed", "failed", "cancelled"]
    state_snapshot: dict  # LangGraph 현재 상태
    started_at: datetime
    completed_at: datetime | None
    error: dict | None
5.2 Database Schema
sql
Copy
-- conversations: 대화 세션
CREATE TABLE conversations (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    status TEXT NOT NULL,
    context JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- intents: 구조화된 의도
CREATE TABLE intents (
    id UUID PRIMARY KEY,
    conversation_id UUID REFERENCES conversations(id),
    domain TEXT NOT NULL,
    goal TEXT NOT NULL,
    tasks JSONB NOT NULL,
    constraints JSONB NOT NULL,
    missing_info TEXT[],
    confidence FLOAT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- agents: 실행 가능한 Agent 정의
CREATE TABLE agents (
    id UUID PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    version TEXT NOT NULL,
    description TEXT NOT NULL,
    domain TEXT[] NOT NULL,
    capabilities TEXT[] NOT NULL,
    input_schema JSONB NOT NULL,
    output_schema JSONB NOT NULL,
    config_schema JSONB NOT NULL,
    code_hash TEXT NOT NULL,
    is_system BOOLEAN DEFAULT FALSE,
    requires_approval BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW()
);

-- workflows: LangGraph 정의
CREATE TABLE workflows (
    id UUID PRIMARY KEY,
    intent_id UUID REFERENCES intents(id),
    name TEXT NOT NULL,
    graph_definition JSONB NOT NULL,
    state JSONB NOT NULL,
    status TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- executions: 실행 이력
CREATE TABLE executions (
    id UUID PRIMARY KEY,
    workflow_id UUID REFERENCES workflows(id),
    status TEXT NOT NULL,
    state_snapshot JSONB NOT NULL,
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error JSONB
);
6. Security & Safety
6.1 Docker Sandbox 격리 정책
yaml
Copy
# Agent 실행 환경 제약
security_opts:
  - no-new-privileges:true  # 권한 상승 방지
read_only: true  # 루트 파일시스템 읽기 전용
tmpfs:
  - /tmp:size=100m  # 임시 파일 용량 제한
mem_limit: 512m  # 메모리 제한
cpu_quota: 50000  # 50% CPU 제한
network_mode: bridge
cap_drop:
  - ALL  # 모든 리눅스 capability 제거
네트워크 화이트리스트:
Agent는 기본적으로 외부 네트워크 접근 차단
필요 시 allowed_hosts: ["api.eodhd.com", "api.slack.com"]만 개별 허용
iptables로 outbound 트래픽 필터링
6.2 Agent Code Safety Checker
Python
Copy
class AgentSafetyChecker:
    FORBIDDEN_PATTERNS = [
        r"os\.system", r"subprocess\.(call|run|Popen)",
        r"eval\s*\(", r"exec\s*\(", r"__import__\s*\(",
        r"open\s*\([^)]*['\"]w['\"]", r"shutil\.rmtree"
    ]
    
    ALLOWED_IMPORTS = {
        "typing", "pydantic", "datetime", "json", "re",
        "asyncio", "aiohttp", "agentforge.sdk"
    }
    
    async def validate(self, code: str) -> SafetyResult:
        # 1. 정규식 기반 금지 패턴 검사
        # 2. AST 파싱으로 import 검증
        # 3. secrets.json, .env 파일 접근 시도 탐지
        # 4. Bandit 정적 분석 도구 연동 (향후)
        pass
6.3 Secrets Management
모든 API 키, 자격 증명은 HashiCorp Vault에 저장
Agent 코드에는 절대 하드코딩 금지
런타임에 환경 변수로 주입: VAULT_SECRET_ID=...
로그에는 자동 마스킹: api_key="sk-...****"
7. Deployment Strategy (모델별 특성)
본 문서는 배포 모델의 기술적 특성만 명세하며, 구체적인 배포 일정은 별도 plan.md에서 다룹니다.
7.1 Self-Hosted Docker (All-in-One)
yaml
Copy
# docker-compose.yml
services:
  agentgaia:
    image: agentgaia/all-in-one:latest
    ports: ["5678:5678"]
    volumes:
      - ./data:/data
      - ./agents:/agents
    environment:
      - DATABASE_URL=postgresql://... (or sqlite:///data/agentgaia.db)
      - LLM_PROVIDER=claude  # or openai, ollama
      - VAULT_ADDR=http://vault:8200
특징:
목표 시작 시간: 5분 이내 (docker compose up -d 한 번)
내장 컴포넌트: API 서버, Worker, PostgreSQL, Redis, NATS, Vault (개발 모드)
LLM 옵션: Ollama 연동으로 완전 오프라인 운영 가능
7.2 Self-Hosted Kubernetes (Enterprise)
yaml
Copy
# values.yaml (Helm Chart)
agentgaia:
  replicas: 3
  components:
    frontend: { replicas: 2 }
    backend: { replicas: 3 }
    worker: { replicas: 5, autoscaling: { enabled: true, min: 2, max: 20 } }
  
  dependencies:
    postgresql: { external: true, host: "rds.amazonaws.com" }
    nats: { cluster: { enabled: true, size: 3 } }
    vault: { external: true, addr: "https://vault.internal" }
특징:
목표 시작 시간: 1일 이내 (Helm install)
고가용성: 각 컴포넌트 다중화
수평 확장: Worker HPA (Horizontal Pod Autoscaling)
7.3 LLM Provider 계층화
yaml
Copy
llm_routing:
  lightweight:
    tasks: ["intent_classification", "execution_explanation", "simple_qa"]
    providers: ["ollama/llama3.1:8b", "claude-haiku"]
    latency_p95: 500ms
    cost_per_1k: $0.001
  
  heavyweight:
    tasks: ["agent_code_generation", "workflow_synthesis", "progressive_clarification"]
    providers: ["claude-sonnet", "gpt-4o", "ollama/llama3.1:70b"]
    latency_p95: 5s
    cost_per_1k: $0.015
환경별 권장 구성:
Table
Copy
환경	기본 LLM	보안	비용	준비사항
개발/테스트	Ollama 8B	⭐⭐⭐⭐⭐	무료	GPU 없어도 CPU 추론 가능
스타트업	Claude API	⭐⭐⭐	중	종량제, 관리 용이
기업 (보안)	vLLM + 70B 로컬	⭐⭐⭐⭐⭐	높음	A100/H100 GPU 필요
에어갭	Ollama 70B	⭐⭐⭐⭐⭐	높음	외부 연결 전혀 없음
8. Success Metrics (객관적 성공 기준)
본 문서는 시간 제한 없는 성공 기준만 정의하며, 달성 일정은 plan.md에서 설정합니다.
8.1 User Experience Metrics
Table
Copy
지표	정의	목표값	측정 방법
Time-to-First-Workflow	첫 방문부터 첫 실행 완료까지	10분 이내	분석 툴 (Mixpanel)
Configuration Completion Rate	설정 시작 대비 완료 비율	80% 이상	이벤트 추적
User Retention (Week 4)	4주차 활성 사용자 비율	40% 이상	DAU/WAU
8.2 System Performance Metrics
Table
Copy
지표	정의	목표값	측정 방법
Intent Parsing Latency (P95)	Intent 생성까지 시간	2초 이내	OpenTelemetry
Workflow Compilation Time	Agent 팀 → LangGraph 변환	1초 이내	Prometheus
Agent Matching Accuracy	Intent 대비 적합 Agent 매칭	90% 이상	수동 샘플 검증
Execution Error Rate	전체 실행 중 실패 비율	5% 이하	Sentry
8.3 Self-Evolution Readiness Metrics
Table
Copy
지표	정의	목표값	측정 방법
Agent Registry Size	사용 가능 Agent 수	100개 이상 (Phase 2)	DB Count
Meta-Agent Generated Agents	자동 생성 Agent 수	50개 이상 (Phase 2)	Registry 필터
Community Forks	커뮤니티 포크 횟수	1,000회/월 (Phase 4)	이벤트 추적
Auto-Improvement Deployed	자동 개선 배포 건수	50건/월 (Phase 3)	Workflow 버전 기록
9. Integration Points
9.1 External Service Connectors
초기 지원 Connector 목록 (MVP):
Finance: EODHD, Alpha Vantage, Yahoo Finance
Communication: Slack, Email (SMTP), Discord
Storage: PostgreSQL, SQLite, CSV
Web: HTTP Request (GET/POST), BeautifulSoup
Connector 정의:
Python
Copy
class Connector(BaseModel):
    id: str
    name: str
    auth_type: Literal["api_key", "oauth2", "basic"]
    base_url: str
    rate_limit: RateLimitConfig
    allowed_in_sandbox: bool = False  # 샌드박스 허용 여부
9.2 Event Streaming Format
NATS Topic: agentgaia.workflow.{workflow_id}.events.{type}
이벤트 스키마:
JSON
Copy
{
  "type": "node.started | node.complete | approval.request | error",
  "workflow_id": "uuid",
  "node_id": "market_data_agent",
  "timestamp": "2025-12-03T10:00:00Z",
  "payload": {
    "explanation": "지금 삼성전자 주식 데이터를 가져오는 중입니다...",
    "result": { "close": 75000, "volume": 1000000 }
  }
}
10. Appendix
10.1 용어집 (Glossary)
Table
Copy
용어	정의
Agent	특정 작업을 수행하는 독립 실행 단위 (Python 함수)
Workflow	Agent들의 실행 순서와 데이터 흐름을 정의한 LangGraph
Intent	사용자 요청을 구조화한 중간 표현 (Pydantic 모델)
Progressive Clarification	불명확한 요소를 대화로 구체화하는 과정
Meta-Agent	새로운 Agent를 생성하는 시스템 (향후 구현)
Human-in-the-Loop	중요 결정 시 사용자 승인을 요구하는 지점
Self-Hosted First	데이터 주권 보호를 위한 온프레미스 배포 우선
10.2 기술적 결정사항 (ADR)
ADR-001: LangGraph 선택
결정: xflow-engine 대신 LangGraph 사용
이유: Human-in-the-Loop, PostgresCheckpointer, 생태계, 인재 풀
결과: 추후 커스텀 엔진 개발 부담 방지
ADR-002: Self-Hosted 우선
결정: SaaS가 아닌 Docker Compose 기본
이유: 금융/법률 데이터 민감성, Bottom-up Adoption
결과: 에어갭, 하이브리드 클라우드 지원 용이
ADR-003: 계층화 LLM 라우팅
결정: Lightweight/Heavyweight Tier 분리
이유: 비용 최적화, 로컬 LLM 오프라인 운영
결과: 개발 환경 무료 운영 가능
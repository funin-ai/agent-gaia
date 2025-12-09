# AgentGaia — Official Tech Spec V5.1
**https://agent-gaia.com**  
**The Self-Evolving Conversational Agent Platform**  
**"Speak Your Expertise — Gaia Grows the Rest"**

버전: 5.1 | 날짜: 2025-12-03 | 상태: Execution-Ready

## 1. 브랜드 & 도메인
- 공식 이름: **AgentGaia**
- 슬로건: **Speak Your Expertise — Gaia Grows the Rest**
- 도메인: agent-gaia.com (Global) / agent-gaia.kr (Korea)

## 2. 핵심 비전
비개발자가 자연어로 말하면 Gaia가 LangGraph 워크플로우를 실시간 생성하고,  
시스템은 스스로 진화하며, 전 세계 전문가들이 Agent를 포크·병합하는 살아있는 생태계가 된다.

## 3. 4단계 성숙도 로드맵 (연도 없는 버전)

| 단계          | 이름                         | 핵심 달성 목표 (이 단계가 끝나면 이렇게 된다)                                                                                 | 완료 기준 (객관적 증거)                                    |
|---------------|------------------------------|-----------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------|
| **Phase 1**   | Speak → Gaia Grows           | 비개발자가 "이렇게 해줘"라고 말하면, Gaia가 완전한 LangGraph 워크플로우를 만들어서 바로 실행해준다.                           | 100명의 비개발자가 코드 한 줄 없이 첫 워크플로우 성공 (7분 이내) |
| **Phase 2**   | Gaia Creates Agents          | 필요한 Agent가 없으면 Gaia가 자동으로 새 Agent를 만들고, 다음 사람부터 바로 재사용 가능                                          | Meta-Agent가 생성한 Agent가 Registry에 100개 이상 누적 + 재사용률 70% |
| **Phase 3**   | Gaia Evolves Itself          | 사용 패턴을 보고 Gaia가 스스로 워크플로우를 더 빠르고 정확하게 개선하며, A/B 테스트 후 승자를 자동 배포                          | 자동 개선된 워크플로우가 월 50건 이상 배포 + 평균 성능 30% 향상     |
| **Phase 4**   | Every Expertise Has Its Agent| 내가 원하는 거의 모든 전문 지식에 대해 "이미 누군가 만들어놓은 최적 Agent가 존재"하는 생태계 완성 → 포크 한 번이면 나만의 버전 완성 | Registry에 10,000개 이상의 커뮤니티 Agent + 월간 포크/병합 1,000건 이상 |

→ 이 4단계는 **시간이 아니라 달성 기준**으로만 움직입니다.  
Phase 1을 3개월 만에 끝내면 2026년 3월에 Phase 2 시작,  
6개월 걸리면 2026년 6월 시작. 연도 예측 없이 순수하게 성과로만 전진.

## 4. 핵심 차별점 (동어반복 제거, 더 날카롭게)

| 항목                  | 다른 모든 도구 (2025 기준) | **AgentGaia**                                    |
|-----------------------|----------------------------|---------------------------------------------------|
| 코드를 써야 하나?      | Yes                       | Never                                             |
| Agent는 누가 만드나?   | 개발자                     | Gaia 스스로 + 커뮤니티                             |
| 워크플로우는 누가 만드나?| 개발자                     | 사용자가 말하면 Gaia가 LangGraph 코드로 생성       |
| 진화는 누가 하나?      | 없거나 수동                | Gaia가 자동으로 (A/B 테스트 + 승자 배포)           |
| 배포는 얼마나 쉬운가?  | 최소 30분~수일             | Docker 실행 후 5분 안에 첫 Agent 실행              |

## 5. 시스템 아키텍처 (4-Layer)
LAYER 1: Speak Interface → 자연어 전용 채팅 + Progressive Clarification
--
LAYER 2: Gaia Brain → Intent Parser + Meta-Agent (LangGraph 코드 생성 엔진)
--
LAYER 3: LangGraph Runtime → 동적 compile + PostgresCheckpointer + astream_events
--
LAYER 4: Gaia Evolution → 패턴 분석 → 자동 개선 → A/B 테스트 → 배포
--

## 6. 기술 스택 (변경 없음, 그대로 유지)

| 계층            | 기술                                           | 비고                              |
|-----------------|------------------------------------------------|-----------------------------------|
| Frontend        | Next.js 15 + Shadcn/UI + React Flow            |                                   |
| Backend         | FastAPI                                        |                                   |
| Core Engine     | LangGraph + PostgresCheckpointer               |                                   |
| Persistence     | PostgreSQL                                     |                                   |
| Cache           | Redis                                          |                                   |
| LLM             | Claude 3.7 (주력) / Llama-3.1-70B (로컬 옵션)   |                                   |
| 배포            | Docker All-in-One → Helm Chart                 | 5분 시작 목표                     |
| Sandbox         | Docker + 네트워크 화이트리스트                   | 동적 코드 안전 실행               |

## 7. 배포 전략

| 유형                | 목표 시작 시간 | 비고                              |
|---------------------|----------------|-----------------------------------|
| All-in-One Docker   | 5분 이내       | `docker run agentgaia/all-in-one` |
| Enterprise Helm     | 1일 이내       |                                   |
| Air-gapped Package  | Phase 3 이후   |                                   |

## 8. 성공 지표 (Phase별)

| Phase | 핵심 지표                            | 목표값                    |
|-------|-------------------------------------|---------------------------|
| 1     | Time-to-First-Workflow              | 평균 7분 이내             |
| 2     | Meta-Agent가 생성한 Agent 누적 수     | 100개 이상                |
| 3     | 자동 개선 배포 건수 (월)             | 50건 이상                 |
| 4     | Registry 내 커뮤니티 Agent 수        | 10,000개 이상             |

## 9. 결론 — 한 문장
**AgentGaia는 코드가 아니라 전문 지식 자체를 심으면 스스로 자라나는 살아있는 생태계다.**

---
**Official Domain**: https://agent-gaia.com  
**Status**: Tech Spec V5.1 최종 확정 → 이제 Plan만 남았다
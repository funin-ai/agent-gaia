# AgentGaia

Multi-LLM RFP 분석 플랫폼

## 기능

- 3개 LLM 동시 분석 (Claude Opus 4.5, GPT-5.1, Gemini 3 Pro)
- 실시간 WebSocket 스트리밍
- PDF 파싱 (80-120 페이지)
- Vault API Key 관리
- 자동 백업 Provider 전환

## 실행

```bash
uv sync
uv run python run.py --env local --reload
```

## 접속

http://localhost:8000

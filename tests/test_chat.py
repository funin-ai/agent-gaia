"""Chat WebSocket integration tests."""

import asyncio
import json
import pytest
import websockets

BASE_URI = "ws://localhost:9033/api/v1/ws/chat"


async def send_and_receive(provider: str, message: str, msg_id: int = 1) -> str:
    """Send message and collect full response."""
    async with websockets.connect(f"{BASE_URI}?provider={provider}") as ws:
        await ws.recv()  # connected message
        await ws.send(json.dumps({
            "type": "chat",
            "message": message,
            "message_id": msg_id
        }))

        response = ""
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("status") == "streaming":
                response += msg.get("chunk", "")
            elif msg.get("status") == "complete":
                break
            elif msg.get("status") == "error":
                raise Exception(msg.get("error"))
        return response


async def clear_history(provider: str = "claude"):
    """Clear conversation history."""
    async with websockets.connect(f"{BASE_URI}?provider={provider}") as ws:
        await ws.recv()
        await ws.send(json.dumps({"type": "clear_history"}))
        await ws.recv()


class TestProviderConnection:
    """Test WebSocket connections to each provider."""

    @pytest.mark.asyncio
    async def test_claude_connection(self):
        async with websockets.connect(f"{BASE_URI}?provider=claude") as ws:
            msg = json.loads(await ws.recv())
            assert msg["type"] == "connected"
            assert msg["provider"] == "claude"

    @pytest.mark.asyncio
    async def test_openai_connection(self):
        async with websockets.connect(f"{BASE_URI}?provider=openai") as ws:
            msg = json.loads(await ws.recv())
            assert msg["type"] == "connected"
            assert msg["provider"] == "openai"

    @pytest.mark.asyncio
    async def test_gemini_connection(self):
        async with websockets.connect(f"{BASE_URI}?provider=gemini") as ws:
            msg = json.loads(await ws.recv())
            assert msg["type"] == "connected"
            assert msg["provider"] == "gemini"


class TestSharedContext:
    """Test conversation context sharing across providers."""

    @pytest.mark.asyncio
    async def test_context_shared_claude_to_openai(self):
        """Claude에서 설정한 컨텍스트를 OpenAI가 기억하는지 확인."""
        await clear_history()

        # Claude에게 정보 전달
        await send_and_receive("claude", "내 이름은 테스트유저야. 기억해.", 1)
        await asyncio.sleep(0.5)

        # OpenAI에게 확인
        response = await send_and_receive("openai", "내 이름이 뭐야?", 2)
        assert "테스트유저" in response

    @pytest.mark.asyncio
    async def test_context_shared_openai_to_gemini(self):
        """OpenAI에서 설정한 컨텍스트를 Gemini가 기억하는지 확인."""
        await clear_history()

        await send_and_receive("openai", "오늘 날씨가 맑다고 가정하자.", 1)
        await asyncio.sleep(0.5)

        response = await send_and_receive("gemini", "오늘 날씨가 어떻다고 했지?", 2)
        assert "맑" in response

    @pytest.mark.asyncio
    async def test_multi_turn_context(self):
        """여러 턴의 대화가 유지되는지 확인."""
        await clear_history()

        await send_and_receive("claude", "숫자 1을 기억해.", 1)
        await asyncio.sleep(0.3)
        await send_and_receive("openai", "그 다음 숫자 2도 기억해.", 2)
        await asyncio.sleep(0.3)
        await send_and_receive("gemini", "그 다음 숫자 3도 기억해.", 3)
        await asyncio.sleep(0.3)

        response = await send_and_receive("claude", "내가 말한 숫자들이 뭐였지?", 4)
        assert "1" in response and "2" in response and "3" in response


class TestClearHistory:
    """Test history clearing functionality."""

    @pytest.mark.asyncio
    async def test_clear_removes_context(self):
        """히스토리 삭제 후 컨텍스트가 사라지는지 확인."""
        # 컨텍스트 설정
        await send_and_receive("claude", "비밀번호는 abc123이야.", 1)

        # 히스토리 삭제
        await clear_history()

        # 컨텍스트 확인
        response = await send_and_receive("claude", "비밀번호가 뭐였지?", 2)
        # 삭제 후에는 비밀번호를 모를 것
        assert "abc123" not in response or "모르" in response or "기억" in response


class TestProviderSwitching:
    """Test seamless provider switching."""

    @pytest.mark.asyncio
    async def test_rapid_switching(self):
        """빠른 프로바이더 전환이 정상 작동하는지 확인."""
        await clear_history()

        providers = ["claude", "openai", "gemini", "claude", "openai"]
        for i, provider in enumerate(providers):
            response = await send_and_receive(provider, f"안녕 {i+1}번째", i+1)
            assert len(response) > 0


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """빈 메시지 처리 확인."""
        async with websockets.connect(f"{BASE_URI}?provider=claude") as ws:
            await ws.recv()
            await ws.send(json.dumps({
                "type": "chat",
                "message": "",
                "message_id": 1
            }))
            msg = json.loads(await ws.recv())
            assert msg.get("status") == "error"


if __name__ == "__main__":
    # 간단한 수동 실행
    async def run_quick_test():
        print("=== Quick Context Sharing Test ===")
        await clear_history()

        print("1. Claude에게 정보 전달...")
        r1 = await send_and_receive("claude", "내 취미는 등산이야.", 1)
        print(f"   Claude: {r1[:80]}...")

        print("2. GPT에게 확인...")
        r2 = await send_and_receive("openai", "내 취미가 뭐라고 했지?", 2)
        print(f"   GPT: {r2[:80]}...")

        print("3. Gemini에게 확인...")
        r3 = await send_and_receive("gemini", "내 취미가 뭐야?", 3)
        print(f"   Gemini: {r3[:80]}...")

        if "등산" in r2 and "등산" in r3:
            print("\n✅ 모든 프로바이더가 컨텍스트 공유 성공!")
        else:
            print("\n❌ 컨텍스트 공유 실패")

    asyncio.run(run_quick_test())

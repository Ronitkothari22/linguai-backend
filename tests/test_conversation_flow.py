import base64

from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.routers.conversations import router as conversations_router
from app.services import conversation_manager
from app.services import llm_service as _llm
from app.services import deepgram_service as _dg


def test_ws_conversation_flow(monkeypatch):
    # Create a session directly in the manager (bypass auth)
    sess = conversation_manager.manager.create_session(user_id="test-user")

    # Stub LLM reply
    def fake_generate_reply(history, user_text, language="English"):
        return "Tutor: Great — I heard you."

    monkeypatch.setattr(_llm.llm_service, "generate_reply", fake_generate_reply)

    # Stub TTS to return fake base64 audio
    fake_audio = base64.b64encode(b"FAKEAUDIO").decode()

    def fake_tts(text, voice="alloy", model=None):
        return {"audio_base64": fake_audio, "mime": "audio/mpeg"}

    monkeypatch.setattr(_dg.deepgram_service, "synthesize_text", fake_tts)

    # create a minimal test app exposing only conversations router to avoid
    # importing full application startup (database etc.)
    test_app = FastAPI()
    test_app.include_router(conversations_router)
    client = TestClient(test_app)

    with client.websocket_connect(f"/conversations/ws/{sess.session_id}") as ws:
        init = ws.receive_json()
        assert init.get("type") == "ready"

        # send a transcript
        ws.send_json({"type": "transcript", "text": "hello world"})
        msg = ws.receive_json()
        assert msg["type"] == "assistant"
        assert "text" in msg
        assert msg["text"] == "Tutor: Great — I heard you."
        assert msg["audio_base64"] == fake_audio
        assert msg["audio_mime"] == "audio/mpeg"

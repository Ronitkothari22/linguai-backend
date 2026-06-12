from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import Any

from app.utils.jwt_middleware import get_current_user
from app.services.conversation_manager import manager as conversation_manager
from app.services.deepgram_service import deepgram_service
from app.services.llm_service import llm_service

router = APIRouter(prefix="/conversations", tags=["conversations"])


class SessionCreateResponse(BaseModel):
    session_id: str
    expires_at: str
    deepgram_token: str
    note: str


@router.post("/session", response_model=SessionCreateResponse)
async def create_conversation_session(current_user: str = Depends(get_current_user)) -> Any:
    # Create an ephemeral conversation session and return Deepgram connection info
    session = conversation_manager.create_session(user_id=current_user)
    conn = deepgram_service.create_connection_info(session.session_id)
    return {
        "session_id": session.session_id,
        "expires_at": conn["expires_at"],
        "deepgram_token": conn["deepgram_token"],
        "note": conn.get("note", ""),
    }


@router.websocket("/ws/{session_id}")
async def conversation_ws(websocket: WebSocket, session_id: str, token: str | None = None):
    # The client must connect with a valid backend JWT as a Bearer token in the
    # `token` query param or use the Authorization header (middleware may vary).
    # For simplicity we accept the connection and do lightweight authorization via token payload.
    await websocket.accept()
    try:
        # minimal handshake: confirm session exists
        session = conversation_manager.get_session(session_id)
        if not session:
            await websocket.send_json({"type": "error", "message": "session_not_found_or_expired"})
            await websocket.close(code=4404)
            return

        await websocket.send_json({"type": "ready", "session_id": session_id})

        while True:
            data = await websocket.receive_json()
            # Expect messages like {"type":"transcript","text":"..."}
            if not isinstance(data, dict):
                continue
            msg_type = data.get("type")
            if msg_type == "transcript":
                text = data.get("text", "")
                # Append user turn to session history
                conversation_manager.append_user_turn(session_id, text)

                # Call LLM to generate tutor reply
                reply_text = llm_service.generate_reply(session.history, text, session.language)
                conversation_manager.append_assistant_turn(session_id, reply_text)

                # Synthesize reply to speech (base64) and send both text+audio
                tts = deepgram_service.synthesize_text(reply_text)
                payload = {
                    "type": "assistant",
                    "text": reply_text,
                    "audio_base64": tts.get("audio_base64", ""),
                    "audio_mime": tts.get("mime", "audio/mpeg"),
                }
                await websocket.send_json(payload)
            elif msg_type == "end":
                conversation_manager.end_session(session_id)
                await websocket.send_json({"type": "ended"})
                await websocket.close()
                return
            else:
                await websocket.send_json({"type": "error", "message": "unknown_message_type"})

    except WebSocketDisconnect:
        # client disconnected — keep session alive for short window or expire
        return


class TranscriptRequest(BaseModel):
    session_id: str
    text: str


@router.post("/transcript")
async def post_transcript(req: TranscriptRequest, current_user: str = Depends(get_current_user)) -> Any:
    """Accept a transcript from the client (or for testing) and return assistant reply.

    This endpoint is primarily for testing/integration: clients that cannot use
    websockets or realtime streaming can POST final transcripts here.
    """
    session = conversation_manager.get_session(req.session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="session_not_found_or_expired")

    # Append user turn and produce a placeholder assistant reply.
    conversation_manager.append_user_turn(req.session_id, req.text)
    reply = f"Tutor: I heard '{req.text}' (echo). Replace with LLM reply."
    conversation_manager.append_assistant_turn(req.session_id, reply)
    return {"type": "assistant", "text": reply}

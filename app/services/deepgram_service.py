from __future__ import annotations

from typing import Dict
import os
import hmac
import hashlib
from datetime import datetime, timedelta

from app.config import get_settings
import base64
import requests


class DeepgramService:
    """Small helper to produce short-lived connection info for Deepgram.

    NOTE: This is a stub implementation. In production, mint Deepgram realtime
    tokens using Deepgram's REST API or relay via a secure proxy. Keep tokens
    short-lived and scoped to a single session.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = getattr(settings, "DEEPGRAM_API_KEY", os.getenv("DEEPGRAM_API_KEY"))
        self.webhook_secret = getattr(
            settings, "DEEPGRAM_WEBHOOK_SECRET", os.getenv("DEEPGRAM_WEBHOOK_SECRET")
        )

    def create_connection_info(self, session_id: str) -> Dict[str, str]:
        # Return a small payload the frontend can use to connect directly to Deepgram.
        # For now we return a placeholder token and instruct the client to use it
        # only for demo/local usage.
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat() + "Z"
        return {
            "deepgram_token": self.api_key or "DEEPGRAM_TEST_TOKEN",
            "session_id": session_id,
            "expires_at": expires_at,
            "note": "Replace with real Deepgram token minting for production",
        }

    def verify_webhook(self, signature: str, body: bytes) -> bool:
        """Verify Deepgram webhook signature.

        Behavior:
        - If no `DEEPGRAM_WEBHOOK_SECRET` is configured, verification is skipped
          (returns True) to allow local/demo workflows.
        - Otherwise, expects an HMAC-SHA256 hex signature. Deepgram may send a
          header like `sha256=<hex>`; we handle both forms.
        """
        if not self.webhook_secret:
            # Signing not configured; accept for local/demo usage.
            return True

        if not signature:
            return False

        # Normalize signature header (allow 'sha256=<hex>' or raw hex)
        sig = signature.split("=", 1)[1] if "=" in signature else signature

        expected = hmac.new(self.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, sig)

    def synthesize_text(self, text: str, voice: str = "alloy", model: str | None = None) -> dict:
        """Synthesize `text` to speech via Deepgram TTS.

        Returns a dict with keys: `audio_base64` and `mime`.
        If no API key is configured, returns a small stub TTS payload.
        """
        api_key = self.api_key
        if not api_key:
            # Return a tiny stub (silence) to allow local testing.
            return {"audio_base64": "", "mime": "audio/mpeg"}

        url = "https://api.deepgram.com/v1/text-to-speech"
        params = {}
        if voice:
            params["voice"] = voice
        if model:
            params["model"] = model

        headers = {"Authorization": f"Token {api_key}", "Content-Type": "application/json"}
        payload = {"text": text}

        try:
            resp = requests.post(url, params=params, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            audio_bytes = resp.content
            audio_b64 = base64.b64encode(audio_bytes).decode()
            mime = resp.headers.get("Content-Type", "audio/mpeg")
            return {"audio_base64": audio_b64, "mime": mime}
        except Exception:
            return {"audio_base64": "", "mime": "audio/mpeg"}


deepgram_service = DeepgramService()

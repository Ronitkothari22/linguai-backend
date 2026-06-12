from __future__ import annotations

from typing import Any
import os

from app.config import get_settings

try:
    from google import genai
except Exception:  # pragma: no cover - tests will mock
    genai = None


MODEL_NAME = "gemini-1.5-flash"


class LLMService:
    def __init__(self) -> None:
        settings = get_settings()
        self.api_key = getattr(settings, "GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))

    def _get_client(self):
        if genai is None:
            raise RuntimeError("genai client not available")
        return genai.Client(api_key=self.api_key)

    def generate_reply(self, session_history: list[dict[str, str]], user_text: str, language: str = "English") -> str:
        """Generate a conversational reply using Gemini.

        The `session_history` is a list of {'role': 'user'|'assistant', 'text': str}.
        We build a simple prompt and return the assistant text.
        """
        # Build a lightweight prompt from history for low latency
        messages = []
        for turn in session_history[-6:]:
            role = "system" if turn.get("role") == "assistant" and turn.get("system") else turn.get("role")
            messages.append(f"{turn.get('role').upper()}: {turn.get('text')}")

        prompt = (
            "You are a helpful language tutor. Keep replies concise and focused on improving the learner's speaking."
            f"\nTarget language: {language}\n\n"
            + "\n".join(messages)
            + f"\nUSER: {user_text}\nASSISTANT:"
        )

        # If genai is available, call it; otherwise produce a simple echo for tests/local
        if genai is None:
            return f"Tutor: I heard '{user_text}' (LLM stub)."

        client = self._get_client()
        resp = client.models.generate_content(
            model=MODEL_NAME,
            contents=prompt,
            config={"max_output_tokens": 200},
        )

        # Extract text safely
        text = getattr(resp, "text", None)
        if isinstance(text, str):
            return text.strip()
        return str(resp)


llm_service = LLMService()

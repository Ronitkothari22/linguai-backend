from __future__ import annotations

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import uuid4


class ConversationSession:
    def __init__(self, user_id: str, language: str = "English") -> None:
        self.session_id = str(uuid4())
        self.user_id = user_id
        self.language = language
        self.created_at = datetime.utcnow()
        self.expires_at = self.created_at + timedelta(hours=1)
        self.last_active = self.created_at
        self.history: List[Dict[str, str]] = []  # list of {role: str, text: str}

    def touch(self) -> None:
        self.last_active = datetime.utcnow()

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at


class ConversationManager:
    """In-memory conversation manager. Replace with Redis for production."""

    def __init__(self) -> None:
        self._sessions: Dict[str, ConversationSession] = {}

    def create_session(self, user_id: str, language: str = "English") -> ConversationSession:
        session = ConversationSession(user_id=user_id, language=language)
        self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        s = self._sessions.get(session_id)
        if s is None:
            return None
        if s.is_expired():
            self._sessions.pop(session_id, None)
            return None
        return s

    def append_user_turn(self, session_id: str, text: str) -> None:
        s = self.get_session(session_id)
        if not s:
            return
        s.history.append({"role": "user", "text": text})
        s.touch()

    def append_assistant_turn(self, session_id: str, text: str) -> None:
        s = self.get_session(session_id)
        if not s:
            return
        s.history.append({"role": "assistant", "text": text})
        s.touch()

    def end_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)


manager = ConversationManager()

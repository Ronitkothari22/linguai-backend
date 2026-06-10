from __future__ import annotations

import os
from datetime import date, datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("AUTH_JWT_SECRET", "test-secret-with-at-least-thirty-two-bytes")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("ENVIRONMENT", "test")

from app.database import get_db_session
from app.main import app
from app.models.lesson import Lesson
from app.models.mistake import Mistake
from app.models.progress import Progress
from app.models.sm2_card import SM2Card
from app.models.user import User
from app.services.ai_evaluator import EvaluationError, EvaluationResult


class FakeScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)

    def first(self):
        return self._items[0] if self._items else None


class FakeResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return FakeScalarResult(self._items)


class FakeAsyncSession:
    def __init__(self):
        self.storage = {
            User: [],
            Lesson: [],
            Mistake: [],
            SM2Card: [],
            Progress: [],
        }

    def _materialize_defaults(self, instance):
        if getattr(instance, "id", None) is None:
            instance.id = uuid4()

        now = datetime.now(timezone.utc)
        if hasattr(instance, "created_at") and getattr(instance, "created_at", None) is None:
            instance.created_at = now
        if hasattr(instance, "updated_at") and getattr(instance, "updated_at", None) is None:
            instance.updated_at = now
        if hasattr(instance, "last_seen") and getattr(instance, "last_seen", None) is None:
            instance.last_seen = now
        if hasattr(instance, "next_review") and getattr(instance, "next_review", None) is None:
            instance.next_review = date.today()

    def add(self, instance):
        self._materialize_defaults(instance)
        bucket = self.storage[type(instance)]
        if instance not in bucket:
            bucket.append(instance)

    async def commit(self):
        return None

    async def execute(self, statement):
        entity = statement.column_descriptions[0].get("entity")
        return FakeResult(self.storage.get(entity, []))


def _build_fake_lesson(user_id: str, topics: list[str]) -> dict:
    exercises = [
        {
            "id": str(uuid4()),
            "type": "fill_blank",
            "prompt": "Complete: Yo ___ al mercado ayer.",
            "answer": "fui",
            "hint": "Past tense of ir.",
            "topic": topics[0],
        },
        {
            "id": str(uuid4()),
            "type": "fill_blank",
            "prompt": "Complete: Necesito ___ mapa.",
            "answer": "un",
            "hint": "Use the correct article.",
            "topic": topics[1] if len(topics) > 1 else topics[0],
        },
        {
            "id": str(uuid4()),
            "type": "sentence_correction",
            "prompt": "Fix: Yo va al hotel ayer.",
            "answer": "Yo fui al hotel ayer.",
            "hint": "Use the past tense.",
            "topic": topics[0],
        },
        {
            "id": str(uuid4()),
            "type": "translation",
            "prompt": "Translate: We are at the station.",
            "answer": "Estamos en la estacion.",
            "hint": "Use estar for location.",
            "topic": topics[2] if len(topics) > 2 else topics[0],
        },
        {
            "id": str(uuid4()),
            "type": "vocabulary_match",
            "prompt": "Match rojo with its meaning.",
            "answer": "red",
            "hint": "It is a color.",
            "topic": topics[3] if len(topics) > 3 else topics[0],
        },
    ]
    return {
        "lesson_id": str(uuid4()),
        "topics": topics,
        "exercises": exercises,
    }


@pytest.fixture
def fake_db():
    return FakeAsyncSession()


@pytest_asyncio.fixture
async def client(fake_db, monkeypatch):
    async def override_db():
        yield fake_db

    async def fake_generate_lesson(user_id, topics, language, level, goal, db):
        lesson = _build_fake_lesson(user_id, topics)
        db.add(
            Lesson(
                id=lesson["lesson_id"],
                user_id=user_id,
                topics=topics,
                content=lesson,
            )
        )
        await db.commit()
        return lesson

    async def fake_evaluate_answer(user_answer, expected_answer, exercise_type, language):
        if user_answer == expected_answer:
            return EvaluationResult(
                errors=[],
                topics_affected=["Past Tense"],
                overall_quality_score=5,
                feedback_message="Perfect answer.",
            )
        return EvaluationResult(
            errors=[
                EvaluationError(
                    type="grammar",
                    description="Wrong tense used.",
                    correction=expected_answer,
                )
            ],
            topics_affected=["Past Tense"],
            overall_quality_score=2,
            feedback_message="Review the past tense form.",
        )

    monkeypatch.setattr("app.routers.lessons.generate_lesson", fake_generate_lesson)
    monkeypatch.setattr("app.routers.lessons.evaluate_answer", fake_evaluate_answer)
    app.dependency_overrides[get_db_session] = override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as test_client:
        yield test_client

    app.dependency_overrides.clear()


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_full_happy_path_register_login_onboard_lesson_submit_dashboard(client, fake_db):
    register_response = await client.post(
        "/auth/register",
        json={"email": "learner@example.com", "password": "secret123", "name": "Learner"},
    )
    assert register_response.status_code == 200
    register_payload = register_response.json()
    user_id = register_payload["user_id"]
    auth_token = register_payload["access_token"]

    assert len(fake_db.storage[User]) == 1
    assert str(fake_db.storage[User][0].id) == user_id

    login_response = await client.post(
        "/auth/login",
        json={"email": "learner@example.com", "password": "secret123"},
    )
    assert login_response.status_code == 200

    onboard_response = await client.post(
        "/onboarding/setup",
        headers=_auth_headers(auth_token),
        json={"language": "Spanish", "level": "beginner", "goal": "travel"},
    )
    assert onboard_response.status_code == 200
    assert len(fake_db.storage[SM2Card]) == 5

    lesson_response = await client.get("/lessons/today", headers=_auth_headers(auth_token))
    assert lesson_response.status_code == 200
    lesson_payload = lesson_response.json()
    assert lesson_payload["exercises"]

    first_exercise = lesson_payload["exercises"][0]
    submit_response = await client.post(
        "/lessons/submit",
        headers=_auth_headers(auth_token),
        json={
            "lesson_id": lesson_payload["lesson_id"],
            "exercise_id": first_exercise["id"],
            "user_answer": "yo va",
        },
    )
    assert submit_response.status_code == 200
    submit_payload = submit_response.json()
    assert submit_payload["topics_updated"] == ["Past Tense"]

    matching_mistakes = [
        row
        for row in fake_db.storage[Mistake]
        if str(row.user_id) == user_id and row.topic == "Past Tense"
    ]
    assert matching_mistakes

    updated_card = next(
        row
        for row in fake_db.storage[SM2Card]
        if str(row.user_id) == user_id and row.topic == "Past Tense"
    )
    assert updated_card.repetition == 0
    assert updated_card.interval == 1

    updated_progress = next(
        row
        for row in fake_db.storage[Progress]
        if str(row.user_id) == user_id and row.topic == "Past Tense"
    )
    assert updated_progress.mastery_score >= 0.0

    lesson_record = fake_db.storage[Lesson][0]
    lesson_record.completed_at = datetime.now(timezone.utc)

    dashboard_response = await client.get("/progress/dashboard", headers=_auth_headers(auth_token))
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.json()
    assert dashboard_payload["streak"] >= 1


@pytest.mark.asyncio
async def test_brand_new_user_gets_starter_lesson(client):
    register_response = await client.post(
        "/auth/register",
        json={"email": "starter@example.com", "password": "secret123", "name": "Starter"},
    )
    token = register_response.json()["access_token"]

    lesson_response = await client.get("/lessons/today", headers=_auth_headers(token))
    assert lesson_response.status_code == 200
    lesson_payload = lesson_response.json()
    assert lesson_payload["topics"]
    assert len(lesson_payload["exercises"]) == 5


@pytest.mark.asyncio
async def test_submitting_same_wrong_answer_twice_increments_frequency_without_duplicate_rows(client, fake_db):
    register_response = await client.post(
        "/auth/register",
        json={"email": "repeat@example.com", "password": "secret123", "name": "Repeat"},
    )
    token = register_response.json()["access_token"]
    await client.post(
        "/onboarding/setup",
        headers=_auth_headers(token),
        json={"language": "Spanish", "level": "beginner", "goal": "travel"},
    )
    lesson_payload = (await client.get("/lessons/today", headers=_auth_headers(token))).json()
    exercise_id = lesson_payload["exercises"][0]["id"]

    body = {
        "lesson_id": lesson_payload["lesson_id"],
        "exercise_id": exercise_id,
        "user_answer": "wrong answer",
    }
    first_submit = await client.post("/lessons/submit", headers=_auth_headers(token), json=body)
    second_submit = await client.post("/lessons/submit", headers=_auth_headers(token), json=body)

    assert first_submit.status_code == 200
    assert second_submit.status_code == 200

    mistakes = fake_db.storage[Mistake]
    assert len(mistakes) == 1
    assert mistakes[0].frequency == 2


@pytest.mark.asyncio
async def test_lessons_today_requires_token(client):
    response = await client.get("/lessons/today")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_lessons_today_accepts_valid_token(client):
    register_response = await client.post(
        "/auth/register",
        json={"email": "secure@example.com", "password": "secret123", "name": "Secure"},
    )
    token = register_response.json()["access_token"]

    response = await client.get("/lessons/today", headers=_auth_headers(token))
    assert response.status_code == 200

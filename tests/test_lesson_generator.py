from datetime import date
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.lesson import Lesson
from app.services.lesson_generator import generate_lesson
from app.services.recommendation import STARTER_TOPICS, get_due_topics

LESSON_RESPONSE = """
{
  "exercises": [
    {
      "type": "fill_blank",
      "prompt": "Complete: Hola, ___ llamo Ana.",
      "answer": "me",
      "hint": "Use the reflexive pronoun.",
      "topic": "Basic Greetings"
    },
    {
      "type": "fill_blank",
      "prompt": "Complete: Tengo ___ libros.",
      "answer": "dos",
      "hint": "It is the Spanish number for two.",
      "topic": "Numbers"
    },
    {
      "type": "sentence_correction",
      "prompt": "Fix: Yo es estudiante.",
      "answer": "Yo soy estudiante.",
      "hint": "Use the correct form of ser.",
      "topic": "Common Verbs"
    },
    {
      "type": "translation",
      "prompt": "Translate: I am at the hotel.",
      "answer": "Estoy en el hotel.",
      "hint": "Use estar for location.",
      "topic": "Present Tense"
    },
    {
      "type": "vocabulary_match",
      "prompt": "Match rojo with its English meaning.",
      "answer": "red",
      "hint": "It is a color.",
      "topic": "Colors"
    }
  ]
}
"""


@pytest.mark.asyncio
async def test_result_always_contains_exactly_five_exercises():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text=LESSON_RESPONSE)
    db = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.lesson_generator._get_model", return_value=model):
        result = await generate_lesson(
            user_id="user-123",
            topics=STARTER_TOPICS["beginner"],
            language="Spanish",
            level="beginner",
            goal="travel",
            db=db,
        )

    assert len(result["exercises"]) == 5


@pytest.mark.asyncio
async def test_each_exercise_has_required_keys():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text=LESSON_RESPONSE)
    db = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.lesson_generator._get_model", return_value=model):
        result = await generate_lesson(
            user_id="user-123",
            topics=STARTER_TOPICS["beginner"],
            language="Spanish",
            level="beginner",
            goal="travel",
            db=db,
        )

    required_keys = {"id", "type", "prompt", "answer", "hint", "topic"}
    for exercise in result["exercises"]:
        assert required_keys.issubset(exercise.keys())
        assert exercise["id"]


@pytest.mark.asyncio
async def test_exercise_types_match_expected_distribution():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text=LESSON_RESPONSE)
    db = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.lesson_generator._get_model", return_value=model):
        result = await generate_lesson(
            user_id="user-123",
            topics=STARTER_TOPICS["beginner"],
            language="Spanish",
            level="beginner",
            goal="travel",
            db=db,
        )

    exercise_types = [exercise["type"] for exercise in result["exercises"]]
    assert exercise_types.count("fill_blank") == 2
    assert exercise_types.count("sentence_correction") == 1
    assert exercise_types.count("translation") == 1
    assert exercise_types.count("vocabulary_match") == 1


@pytest.mark.asyncio
async def test_lesson_is_saved_to_db():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(text=LESSON_RESPONSE)
    db = MagicMock()
    db.commit = AsyncMock()

    with patch("app.services.lesson_generator._get_model", return_value=model):
        result = await generate_lesson(
            user_id="user-123",
            topics=STARTER_TOPICS["beginner"],
            language="Spanish",
            level="beginner",
            goal="travel",
            db=db,
        )

    db.add.assert_called_once()
    saved_lesson = db.add.call_args.args[0]
    assert isinstance(saved_lesson, Lesson)
    assert saved_lesson.user_id == "user-123"
    assert saved_lesson.topics == STARTER_TOPICS["beginner"]
    assert saved_lesson.content == result
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_due_topics_returns_most_overdue_topics_first():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(
            all=lambda: ["Past Tense", "Articles", "Conditionals"]
        )
    )

    result = await get_due_topics("user-123", db, "intermediate")

    db.execute.assert_awaited_once()
    statement = db.execute.call_args.args[0]
    compiled_sql = str(statement)

    assert result == ["Past Tense", "Articles", "Conditionals"]
    assert "ORDER BY sm2_cards.next_review ASC" in compiled_sql
    assert "LIMIT" in compiled_sql
    assert statement.compile().params["next_review_1"] == date.today()


@pytest.mark.asyncio
async def test_get_due_topics_returns_starter_topics_when_no_cards_are_due():
    db = AsyncMock()
    db.execute.return_value = SimpleNamespace(
        scalars=lambda: SimpleNamespace(all=lambda: [])
    )

    result = await get_due_topics("user-123", db, "advanced")

    assert result == STARTER_TOPICS["advanced"]

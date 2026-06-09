from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

import google.generativeai as genai
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.lesson import Lesson as LessonModel

MODEL_NAME = "gemini-1.5-flash"
EXERCISE_DISTRIBUTION = {
    "fill_blank": 2,
    "sentence_correction": 1,
    "translation": 1,
    "vocabulary_match": 1,
}


class GeneratedExercise(BaseModel):
    type: str
    prompt: str
    answer: str
    hint: str | None = None
    topic: str


class GeneratedLessonPayload(BaseModel):
    exercises: list[GeneratedExercise] = Field(min_length=5, max_length=5)


def _get_model() -> genai.GenerativeModel:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    return genai.GenerativeModel(MODEL_NAME)


def _build_prompt(topics: list[str], language: str, level: str, goal: str) -> str:
    topics_text = ", ".join(topics)
    return f"""You are a language lesson generator for LinguAI.
Return ONLY valid JSON. No markdown. No preamble. No backticks.

Generate exactly 5 exercises for a {level} learner studying {language} for {goal}.
The lesson must focus on these topics: {topics_text}.

Use this exact exercise distribution:
- 2 fill_blank
- 1 sentence_correction
- 1 translation
- 1 vocabulary_match

Each exercise must be an object with these keys:
- type
- prompt
- answer
- hint
- topic

Return JSON with this exact shape:
{{
  "exercises": [
    {{
      "type": "fill_blank",
      "prompt": "Question text",
      "answer": "Correct answer",
      "hint": "Helpful hint",
      "topic": "Topic Name"
    }}
  ]
}}"""


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", "")
    if isinstance(text, str):
        return text.strip()
    return str(text).strip()


def _parse_generated_lesson(raw_text: str) -> list[GeneratedExercise]:
    payload = json.loads(raw_text)
    validated = GeneratedLessonPayload.model_validate(payload)
    return validated.exercises


def _normalize_exercises(exercises: list[GeneratedExercise]) -> list[dict[str, Any]]:
    normalized_exercises = []
    for exercise in exercises:
        normalized_exercises.append(
            {
                "id": str(uuid4()),
                "type": exercise.type,
                "prompt": exercise.prompt,
                "answer": exercise.answer,
                "hint": exercise.hint,
                "topic": exercise.topic,
            }
        )
    return normalized_exercises


async def generate_lesson(
    user_id: str,
    topics: list[str],
    language: str,
    level: str,
    goal: str,
    db: AsyncSession,
) -> dict[str, Any]:
    prompt = _build_prompt(topics=topics, language=language, level=level, goal=goal)
    model = _get_model()
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )

    try:
        exercises = _parse_generated_lesson(_extract_response_text(response))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError("Gemini returned an invalid lesson payload") from exc

    lesson = {
        "lesson_id": str(uuid4()),
        "topics": topics,
        "exercises": _normalize_exercises(exercises),
    }

    lesson_record = LessonModel(
        id=lesson["lesson_id"],
        user_id=user_id,
        topics=topics,
        content=lesson,
    )
    db.add(lesson_record)
    await db.commit()

    return lesson

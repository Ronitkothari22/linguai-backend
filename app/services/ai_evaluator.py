from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, Field, ValidationError
from google import genai

from app.config import get_settings

MODEL_NAME = "gemini-1.5-flash"
SYSTEM_PROMPT = """You are a language learning evaluation engine.
Your job is to analyze a student's answer and identify any language errors.
You must respond ONLY with a valid JSON object. No explanation. No markdown. No preamble. No backticks.
The JSON must match this exact schema:
{
  "errors": [
    {
      "type": "grammar or vocabulary or pronunciation or spelling",
      "description": "brief explanation of what was wrong",
      "correction": "the corrected word or phrase"
    }
  ],
  "topics_affected": ["Topic Name"],
  "overall_quality_score": 0,
  "feedback_message": "short helpful feedback for the learner"
}
The overall_quality_score must be an integer from 0 to 5."""


class EvaluationError(BaseModel):
    type: str
    description: str
    correction: str


class EvaluationResult(BaseModel):
    errors: list[EvaluationError] = Field(default_factory=list)
    topics_affected: list[str] = Field(default_factory=list)
    overall_quality_score: int = Field(ge=0, le=5)
    feedback_message: str


def _get_client() -> genai.Client:
    settings = get_settings()
    return genai.Client(api_key=settings.gemini_api_key)


def _build_prompt(
    user_answer: str,
    expected_answer: str,
    exercise_type: str,
    language: str,
) -> str:
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"Target language: {language}\n"
        f"Exercise type: {exercise_type}\n"
        f"Expected correct answer: {expected_answer}\n"
        f"Student answer: {user_answer}\n"
    )


def _extract_response_text(response: Any) -> str:
    text = getattr(response, "text", "")
    if isinstance(text, str):
        return text.strip()
    return str(text).strip()


def _generate_content(prompt: str) -> Any:
    client = _get_client()
    return client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )


def _parse_evaluation_response(raw_text: str) -> EvaluationResult:
    payload = json.loads(raw_text)
    return EvaluationResult.model_validate(payload)


def _fallback_result() -> EvaluationResult:
    return EvaluationResult(
        errors=[],
        topics_affected=[],
        overall_quality_score=0,
        feedback_message=(
            "We could not evaluate this answer right now. Please review the "
            "correct answer and try again."
        ),
    )


async def evaluate_answer(
    user_answer: str,
    expected_answer: str,
    exercise_type: str,
    language: str,
) -> EvaluationResult:
    prompt = _build_prompt(
        user_answer=user_answer,
        expected_answer=expected_answer,
        exercise_type=exercise_type,
        language=language,
    )

    for _ in range(2):
        try:
            response = _generate_content(prompt)
            return _parse_evaluation_response(_extract_response_text(response))
        except (json.JSONDecodeError, ValidationError, Exception):
            continue

    return _fallback_result()

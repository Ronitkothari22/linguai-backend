from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services.ai_evaluator import EvaluationResult, evaluate_answer


@pytest.mark.asyncio
async def test_correct_answer_mock_returns_quality_five_and_empty_errors_list():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(
        text="""
        {
          "errors": [],
          "topics_affected": ["Present Tense"],
          "overall_quality_score": 5,
          "feedback_message": "Perfect answer."
        }
        """
    )

    with patch("app.services.ai_evaluator._get_model", return_value=model):
        result = await evaluate_answer(
            user_answer="Hola",
            expected_answer="Hola",
            exercise_type="translation",
            language="Spanish",
        )

    assert isinstance(result, EvaluationResult)
    assert result.overall_quality_score == 5
    assert result.errors == []


@pytest.mark.asyncio
async def test_wrong_tense_mock_returns_grammar_error_and_past_tense_topic():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(
        text="""
        {
          "errors": [
            {
              "type": "grammar",
              "description": "Wrong tense used.",
              "correction": "went"
            }
          ],
          "topics_affected": ["Past Tense"],
          "overall_quality_score": 2,
          "feedback_message": "Review the past tense form of go."
        }
        """
    )

    with patch("app.services.ai_evaluator._get_model", return_value=model):
        result = await evaluate_answer(
            user_answer="I go market yesterday",
            expected_answer="I went to the market yesterday",
            exercise_type="sentence_correction",
            language="English",
        )

    assert result.errors[0].type == "grammar"
    assert "Past Tense" in result.topics_affected


@pytest.mark.asyncio
async def test_missing_article_mock_returns_grammar_error():
    model = MagicMock()
    model.generate_content.return_value = SimpleNamespace(
        text="""
        {
          "errors": [
            {
              "type": "grammar",
              "description": "Missing article before noun.",
              "correction": "the market"
            }
          ],
          "topics_affected": ["Articles"],
          "overall_quality_score": 3,
          "feedback_message": "Remember to include the article."
        }
        """
    )

    with patch("app.services.ai_evaluator._get_model", return_value=model):
        result = await evaluate_answer(
            user_answer="I went to market",
            expected_answer="I went to the market",
            exercise_type="fill_blank",
            language="English",
        )

    assert result.errors
    assert result.errors[0].type == "grammar"


@pytest.mark.asyncio
async def test_malformed_gemini_response_triggers_retry_and_then_returns_fallback():
    model = MagicMock()
    model.generate_content.side_effect = [
        SimpleNamespace(text="not valid json"),
        SimpleNamespace(text="{still not valid json"),
    ]

    with patch("app.services.ai_evaluator._get_model", return_value=model):
        result = await evaluate_answer(
            user_answer="Bonjour",
            expected_answer="Bonjour",
            exercise_type="translation",
            language="French",
        )

    assert model.generate_content.call_count == 2
    assert result.overall_quality_score == 0


@pytest.mark.asyncio
async def test_fallback_response_has_quality_zero_and_non_empty_feedback_message():
    with patch(
        "app.services.ai_evaluator._get_model",
        side_effect=RuntimeError("Gemini unavailable"),
    ):
        result = await evaluate_answer(
            user_answer="Hallo",
            expected_answer="Hallo",
            exercise_type="translation",
            language="German",
        )

    assert result.overall_quality_score == 0
    assert result.feedback_message

from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.lesson import Lesson as LessonModel
from app.models.mistake import Mistake
from app.models.progress import Progress
from app.models.sm2_card import SM2Card
from app.models.user import User
from app.schemas.lesson import LessonSubmitRequest, LessonSubmitResponse
from app.services.ai_evaluator import evaluate_answer
from app.services.lesson_generator import generate_lesson
from app.services.recommendation import get_due_topics
from app.services.sm2_engine import update_sm2
from app.utils.jwt_middleware import get_current_user

router = APIRouter(prefix="/lessons", tags=["lessons"])


class LessonHistoryResponse(BaseModel):
    items: list[dict]
    limit: int
    offset: int


def _today_utc() -> date:
    return datetime.now(timezone.utc).date()


def _is_same_day(timestamp: datetime | None, target_date: date) -> bool:
    if timestamp is None:
        return False
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc).date() == target_date


def _calculate_mastery_score(ease_factor: float, quality: int) -> float:
    ease_component = (ease_factor - 1.3) / (2.5 - 1.3)
    quality_component = quality / 5
    mastery = (ease_component * 0.7) + (quality_component * 0.3)
    return round(max(0.0, min(1.0, mastery)), 4)


def _serialize_lesson_record(record: LessonModel) -> dict:
    return {
        "lesson_id": str(record.id),
        "topics": record.topics,
        "content": record.content,
        "score": record.score,
        "completed_at": record.completed_at.isoformat() if record.completed_at else None,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


@router.get("/today")
async def get_today_lesson(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> dict:
    today = _today_utc()
    lessons = [
        lesson
        for lesson in (await db.execute(select(LessonModel))).scalars().all()
        if str(lesson.user_id) == str(current_user.id)
    ]
    lessons.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)

    existing_today = next((lesson for lesson in lessons if _is_same_day(lesson.created_at, today)), None)
    if existing_today is not None:
        return existing_today.content

    topics = await get_due_topics(str(current_user.id), db, current_user.level or "beginner")
    return await generate_lesson(
        user_id=str(current_user.id),
        topics=topics,
        language=current_user.language or "Spanish",
        level=current_user.level or "beginner",
        goal=current_user.goal or "casual",
        db=db,
    )


@router.post("/submit", response_model=LessonSubmitResponse)
async def submit_lesson_answer(
    payload: LessonSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> LessonSubmitResponse:
    lessons = [
        lesson
        for lesson in (await db.execute(select(LessonModel))).scalars().all()
        if str(lesson.user_id) == str(current_user.id)
    ]
    lesson = next((item for item in lessons if str(item.id) == payload.lesson_id), None)
    if lesson is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found")

    exercise = next(
        (item for item in lesson.content.get("exercises", []) if item.get("id") == payload.exercise_id),
        None,
    )
    if exercise is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found")

    evaluation = await evaluate_answer(
        user_answer=payload.user_answer,
        expected_answer=exercise["answer"],
        exercise_type=exercise["type"],
        language=current_user.language or "Spanish",
    )

    topics_to_update = evaluation.topics_affected or [exercise["topic"]]
    mistake_records = [
        item
        for item in (await db.execute(select(Mistake))).scalars().all()
        if str(item.user_id) == str(current_user.id)
    ]
    sm2_cards = {
        card.topic: card
        for card in (await db.execute(select(SM2Card))).scalars().all()
        if str(card.user_id) == str(current_user.id)
    }
    progress_rows = {
        row.topic: row
        for row in (await db.execute(select(Progress))).scalars().all()
        if str(row.user_id) == str(current_user.id)
    }

    error_types = sorted({error.type for error in evaluation.errors}) or ["grammar"]
    if evaluation.overall_quality_score < 5:
        for topic in topics_to_update:
            for error_type in error_types:
                existing_mistake = next(
                    (
                        record
                        for record in mistake_records
                        if record.topic == topic and record.error_type == error_type
                    ),
                    None,
                )
                if existing_mistake is None:
                    db.add(
                        Mistake(
                            user_id=current_user.id,
                            topic=topic,
                            error_type=error_type,
                            frequency=1,
                            last_seen=datetime.now(timezone.utc),
                        )
                    )
                else:
                    existing_mistake.frequency += 1
                    existing_mistake.last_seen = datetime.now(timezone.utc)

    mastery_snapshot: list[dict] = []
    for topic in topics_to_update:
        card = sm2_cards.get(topic)
        if card is None:
            card = SM2Card(
                user_id=current_user.id,
                topic=topic,
                ease_factor=2.5,
                interval=1,
                repetition=0,
                next_review=_today_utc(),
            )
            db.add(card)
            sm2_cards[topic] = card

        sm2_result = update_sm2(
            quality=evaluation.overall_quality_score,
            ease_factor=card.ease_factor,
            interval=card.interval,
            repetition=card.repetition,
        )
        card.ease_factor = float(sm2_result["ease_factor"])
        card.interval = int(sm2_result["interval"])
        card.repetition = int(sm2_result["repetition"])
        card.next_review = sm2_result["next_review_date"]

        mastery_score = _calculate_mastery_score(card.ease_factor, evaluation.overall_quality_score)
        progress_row = progress_rows.get(topic)
        if progress_row is None:
            progress_row = Progress(
                user_id=current_user.id,
                topic=topic,
                mastery_score=mastery_score,
            )
            db.add(progress_row)
            progress_rows[topic] = progress_row
        else:
            progress_row.mastery_score = mastery_score
            progress_row.updated_at = datetime.now(timezone.utc)

        mastery_snapshot.append(
            {
                "topic": topic,
                "mastery_score": mastery_score,
                "next_review": card.next_review.isoformat(),
            }
        )

    submissions = lesson.content.setdefault("submissions", {})
    submissions[payload.exercise_id] = {
        "user_answer": payload.user_answer,
        "evaluation": evaluation.model_dump(),
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }
    scores = [
        submission["evaluation"]["overall_quality_score"]
        for submission in submissions.values()
        if "evaluation" in submission
    ]
    lesson.score = round(sum(scores) / len(scores), 2) if scores else None
    if len(submissions) >= len(lesson.content.get("exercises", [])):
        lesson.completed_at = datetime.now(timezone.utc)

    await db.commit()

    return LessonSubmitResponse(
        evaluation=evaluation.model_dump(),
        topics_updated=topics_to_update,
        mastery_snapshot=mastery_snapshot,
    )


@router.get("/history", response_model=LessonHistoryResponse)
async def get_lesson_history(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> LessonHistoryResponse:
    lessons = [
        lesson
        for lesson in (await db.execute(select(LessonModel))).scalars().all()
        if str(lesson.user_id) == str(current_user.id)
    ]
    lessons.sort(key=lambda item: item.created_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    paginated = lessons[offset : offset + limit]

    return LessonHistoryResponse(
        items=[_serialize_lesson_record(lesson) for lesson in paginated],
        limit=limit,
        offset=offset,
    )

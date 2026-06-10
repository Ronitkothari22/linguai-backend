from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.lesson import Lesson as LessonModel
from app.models.mistake import Mistake
from app.models.progress import Progress
from app.models.sm2_card import SM2Card
from app.models.user import User
from app.schemas.progress import DashboardResponse, ProgressResponse, WeakTopicResponse
from app.utils.jwt_middleware import get_current_user

router = APIRouter(prefix="/progress", tags=["progress"])


def _calculate_streak(completed_lessons: list[LessonModel]) -> int:
    completion_days = set()
    for lesson in completed_lessons:
        if lesson.completed_at is None:
            continue
        completed_at = lesson.completed_at
        if completed_at.tzinfo is None:
            completed_at = completed_at.replace(tzinfo=timezone.utc)
        completion_days.add(completed_at.astimezone(timezone.utc).date())

    streak = 0
    current_day = datetime.now(timezone.utc).date()
    while current_day in completion_days:
        streak += 1
        current_day -= timedelta(days=1)
    return streak


@router.get("/dashboard", response_model=DashboardResponse)
async def get_progress_dashboard(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> DashboardResponse:
    progress_rows = [
        row
        for row in (await db.execute(select(Progress))).scalars().all()
        if str(row.user_id) == str(current_user.id)
    ]
    lessons = [
        lesson
        for lesson in (await db.execute(select(LessonModel))).scalars().all()
        if str(lesson.user_id) == str(current_user.id)
    ]
    weak_topics_count = sum(1 for row in progress_rows if row.mastery_score < 0.6)

    return DashboardResponse(
        streak=_calculate_streak(lessons),
        mastery_levels=[
            ProgressResponse(topic=row.topic, mastery_score=row.mastery_score)
            for row in sorted(progress_rows, key=lambda item: item.topic)
        ],
        total_lessons=len(lessons),
        weak_topics_count=weak_topics_count,
    )


@router.get("/weak-topics", response_model=list[WeakTopicResponse])
async def get_weak_topics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> list[WeakTopicResponse]:
    progress_rows = [
        row
        for row in (await db.execute(select(Progress))).scalars().all()
        if str(row.user_id) == str(current_user.id) and row.mastery_score < 0.6
    ]
    sm2_cards = {
        card.topic: card
        for card in (await db.execute(select(SM2Card))).scalars().all()
        if str(card.user_id) == str(current_user.id)
    }
    mistakes = [
        row
        for row in (await db.execute(select(Mistake))).scalars().all()
        if str(row.user_id) == str(current_user.id)
    ]

    response: list[WeakTopicResponse] = []
    for row in sorted(progress_rows, key=lambda item: item.mastery_score):
        topic_frequency = sum(mistake.frequency for mistake in mistakes if mistake.topic == row.topic)
        next_review = sm2_cards.get(row.topic).next_review if row.topic in sm2_cards else None
        response.append(
            WeakTopicResponse(
                topic=row.topic,
                mastery_score=row.mastery_score,
                next_review=next_review.isoformat() if next_review else "",
                frequency=topic_frequency,
            )
        )

    return response

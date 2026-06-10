from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.progress import Progress
from app.models.sm2_card import SM2Card
from app.models.user import User
from app.schemas.user import UserProfile
from app.services.recommendation import STARTER_TOPICS
from app.utils.jwt_middleware import get_current_user

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class OnboardingSetupRequest(BaseModel):
    language: str
    level: str
    goal: str


class OnboardingSetupResponse(BaseModel):
    user_profile: UserProfile
    starter_topics: list[str]


def _to_user_profile(user: User) -> UserProfile:
    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        language=user.language,
        level=user.level,
        goal=user.goal,
    )


@router.post("/setup", response_model=OnboardingSetupResponse)
async def setup_onboarding(
    payload: OnboardingSetupRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingSetupResponse:
    level_key = payload.level.lower()
    starter_topics = STARTER_TOPICS.get(level_key, STARTER_TOPICS["beginner"])

    current_user.language = payload.language
    current_user.level = level_key
    current_user.goal = payload.goal.lower()

    existing_cards = {
        card.topic: card
        for card in (await db.execute(select(SM2Card))).scalars().all()
        if str(card.user_id) == str(current_user.id)
    }
    existing_progress = {
        item.topic: item
        for item in (await db.execute(select(Progress))).scalars().all()
        if str(item.user_id) == str(current_user.id)
    }

    for topic in starter_topics:
        if topic not in existing_cards:
            db.add(
                SM2Card(
                    user_id=current_user.id,
                    topic=topic,
                    ease_factor=2.5,
                    interval=1,
                    repetition=0,
                    next_review=date.today(),
                )
            )
        if topic not in existing_progress:
            db.add(Progress(user_id=current_user.id, topic=topic, mastery_score=0.0))

    await db.commit()

    return OnboardingSetupResponse(
        user_profile=_to_user_profile(current_user),
        starter_topics=starter_topics,
    )

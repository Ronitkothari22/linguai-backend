from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sm2_card import SM2Card

STARTER_TOPICS = {
    "beginner": [
        "Basic Greetings",
        "Numbers",
        "Colors",
        "Common Verbs",
        "Present Tense",
    ],
    "intermediate": [
        "Past Tense",
        "Future Tense",
        "Prepositions",
        "Articles",
        "Conditionals",
    ],
    "advanced": [
        "Subjunctive Mood",
        "Idiomatic Expressions",
        "Complex Sentences",
        "Formal Register",
        "Pronunciation Nuance",
    ],
}


async def get_due_topics(user_id: str, db: AsyncSession, level: str) -> list[str]:
    normalized_level = level.lower()
    fallback_topics = STARTER_TOPICS.get(normalized_level, STARTER_TOPICS["beginner"])

    statement = (
        select(SM2Card.topic)
        .where(SM2Card.user_id == user_id, SM2Card.next_review <= date.today())
        .order_by(SM2Card.next_review.asc())
        .limit(5)
    )
    result = await db.execute(statement)
    topics = list(result.scalars().all())

    return topics or fallback_topics

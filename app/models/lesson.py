from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import Float, ForeignKey, Text, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topics: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    score: Mapped[float | None] = mapped_column(Float)
    completed_at = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    created_at = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )

from uuid import uuid4

from sqlalchemy import ForeignKey, Integer, Text, TIMESTAMP, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Mistake(Base):
    __tablename__ = "mistakes"
    __table_args__ = (UniqueConstraint("user_id", "topic", "error_type"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(Text, nullable=False)
    error_type: Mapped[str] = mapped_column(Text, nullable=False)
    frequency: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    last_seen = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    created_at = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

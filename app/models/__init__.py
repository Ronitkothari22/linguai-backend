from sqlalchemy.orm import declarative_base

Base = declarative_base()

from app.models.lesson import Lesson  # noqa: E402,F401
from app.models.mistake import Mistake  # noqa: E402,F401
from app.models.progress import Progress  # noqa: E402,F401
from app.models.sm2_card import SM2Card  # noqa: E402,F401
from app.models.user import User  # noqa: E402,F401

from datetime import date

from pydantic import BaseModel


class SM2CardResponse(BaseModel):
    id: str
    user_id: str
    topic: str
    ease_factor: float
    interval: int
    repetition: int
    next_review: date

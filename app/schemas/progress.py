from pydantic import BaseModel


class ProgressResponse(BaseModel):
    topic: str
    mastery_score: float


class DashboardResponse(BaseModel):
    streak: int
    mastery_levels: list[ProgressResponse]
    total_lessons: int
    weak_topics_count: int


class WeakTopicResponse(BaseModel):
    topic: str
    mastery_score: float
    next_review: str
    frequency: int

from pydantic import BaseModel


class Exercise(BaseModel):
    id: str
    type: str
    prompt: str
    answer: str
    hint: str | None = None
    topic: str


class Lesson(BaseModel):
    lesson_id: str
    topics: list[str]
    exercises: list[Exercise]


class LessonSubmitRequest(BaseModel):
    lesson_id: str
    exercise_id: str
    user_answer: str


class LessonSubmitResponse(BaseModel):
    evaluation: dict
    topics_updated: list[str]
    mastery_snapshot: list[dict]

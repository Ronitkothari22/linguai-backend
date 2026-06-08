from pydantic import BaseModel


class MistakeCreate(BaseModel):
    topic: str
    error_type: str


class MistakeResponse(BaseModel):
    id: str
    user_id: str
    topic: str
    error_type: str
    frequency: int

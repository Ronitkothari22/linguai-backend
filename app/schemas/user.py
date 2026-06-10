from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    user_id: str
    email: str
    access_token: str


class LoginResponse(BaseModel):
    access_token: str
    user_profile: "UserProfile"


class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    language: str
    level: str
    goal: str


LoginResponse.model_rebuild()

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.models.user import User
from app.schemas.user import LoginRequest, LoginResponse, UserCreate, UserProfile, UserResponse
from app.utils.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LogoutResponse(BaseModel):
    success: bool
    message: str


def _to_user_profile(user: User) -> UserProfile:
    return UserProfile(
        id=str(user.id),
        email=user.email,
        name=user.name,
        language=user.language,
        level=user.level,
        goal=user.goal,
    )


@router.post("/register", response_model=UserResponse)
async def register(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    existing_users = (await db.execute(select(User))).scalars().all()
    if any(user.email.lower() == payload.email.lower() for user in existing_users):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email already exists",
        )

    user = User(
        email=payload.email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        language="",
        level="",
        goal="",
    )
    db.add(user)
    await db.commit()

    return UserResponse(
        user_id=str(user.id),
        email=user.email,
        access_token=create_access_token(str(user.id)),
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> LoginResponse:
    users = (await db.execute(select(User))).scalars().all()
    user = next((row for row in users if row.email.lower() == payload.email.lower()), None)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    return LoginResponse(
        access_token=create_access_token(str(user.id)),
        user_profile=_to_user_profile(user),
    )


@router.post("/logout", response_model=LogoutResponse)
async def logout() -> LogoutResponse:
    return LogoutResponse(
        success=True,
        message="Client should clear its stored session token",
    )

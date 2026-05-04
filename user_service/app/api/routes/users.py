from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.responses import UserMeResponse
from app.schemas.user import UserProfile, UserProfileUpdate
from app.db.session import AsyncSession, AsyncSessionLocal

router = APIRouter()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@router.get("/me", response_model=UserMeResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return UserMeResponse(
        message="Your profile was loaded successfully.",
        user=UserProfile.model_validate(current_user),
    )


@router.put("/me", response_model=UserMeResponse)
async def update_user_profile(
    user_profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    for field, value in user_profile.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="That phone number is already registered to another account. Please use a different number.",
        )
    await db.refresh(current_user)
    return UserMeResponse(
        message="Your profile was updated successfully.",
        user=UserProfile.model_validate(current_user),
    )

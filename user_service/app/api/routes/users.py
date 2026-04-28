from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.user import UserProfileUpdate
from app.db.session import AsyncSession, AsyncSessionLocal

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

@router.get("/me")
async def get_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/me")
async def update_user_profile(user_profile: UserProfileUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    for field, value in user_profile.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    await db.commit()
    return current_user
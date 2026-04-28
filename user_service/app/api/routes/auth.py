from fastapi import APIRouter, Depends, HTTPException
from app.core.security import decode_token
from app.api.deps import get_current_user
from app.schemas.user import UserCreate, UserLogin
from app.services.user_service import create_user, authenticate_user
from app.db.session import AsyncSession, AsyncSessionLocal
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from jose import JWTError
from app.models.refresh_token import RefreshToken
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from sqlalchemy.future import select
from app.core.security import hash_password, verify_password


router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

@router.post("/signup")
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    return await create_user(db, user.email, user.password)

@router.post("/login")
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    db_user = await authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    # TODO: enable once email verification is implemented
    # if not db_user.is_verified:
    #     raise HTTPException(status_code=401, detail="Email not verified")

    access_token = create_access_token({"sub": db_user.email})
    refresh_token = create_refresh_token({"sub": db_user.email})

    db_token = RefreshToken(
        user_id=db_user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()
    return {"access_token": access_token, "refresh_token": refresh_token}

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password")
async def change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):

    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    current_user.hashed_password = hash_password(data.new_password)
    db.add(current_user)
    await db.commit()
    return {"message": "Password changed successfully"}

@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    return {"message": "Password reset email sent"}

@router.post("/reset-password")
async def reset_password(token: str, password: str):
    return {"message": "Password reset successfully"}

@router.post("/send-verification")
async def send_verification(email: EmailStr):
    return {"message": "Verification email sent"}

@router.post("/verify-email")
async def verify_email(token: str):
    return {"message": "Email verified successfully", "is_verified": True}

@router.post("/logout")
async def logout(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked == False
    ))
    db_token = result.scalar_one_or_none()
    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid token")
    db_token.is_revoked = True
    db.add(db_token)
    await db.commit()
    return {"message": "Logged out successfully"}

@router.post("/logout-all")
async def logout_all(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.user_id == current_user.id
    ))
    db_tokens = result.scalars().all()
    for db_token in db_tokens:
        db_token.is_revoked = True
        db.add(db_token)
    await db.commit()
    return {"message": "Logged out from all devices successfully"}

class RefreshTokenRequest(BaseModel):
    refresh_token: str
@router.post("/refresh")
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    refresh_token = data.refresh_token
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    result = await db.execute(
    select(User).where(User.email == payload["sub"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    # Rotate refresh token
    db_token.is_revoked = True

    new_access_token = create_access_token({"sub": payload["sub"]})
    new_refresh_token = create_refresh_token({"sub": payload["sub"]})

    db.add(RefreshToken(
        user_id=user.id,
        token=new_refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    ))
    await db.commit()

    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token
    }
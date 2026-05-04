from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.future import select

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User

security = HTTPBearer()


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Your access token is invalid or has expired. Please sign in again.",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="This token cannot be used here. Please use a valid access token.",
        )

    return payload


async def get_current_user(
    token_data: dict = Depends(get_current_user_token),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == token_data["sub"])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="We could not find your account. It may have been removed.",
            )

        return user
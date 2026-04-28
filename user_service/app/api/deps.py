from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.user import User
from sqlalchemy.future import select

security = HTTPBearer()

def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")

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
            raise HTTPException(status_code=404, detail="User not found")

        return user
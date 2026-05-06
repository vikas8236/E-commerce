from datetime import datetime, timedelta

from jose import JWTError, jwt

from app.core.config import ALGORITHM, SECRET_KEY

ACCESS_TOKEN_EXPIRE_MINUTES = 15


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


__all__ = ["JWTError", "create_access_token", "decode_token"]

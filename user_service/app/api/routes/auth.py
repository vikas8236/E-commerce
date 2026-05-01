import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi_mail.errors import ConnectionErrors
from app.core.security import decode_token
from app.api.deps import get_current_user
from app.schemas.user import UserCreate, UserLogin, UserProfile
from app.services.user_service import create_user, authenticate_user
from app.db.session import AsyncSession, AsyncSessionLocal
from app.core.security import create_access_token, create_refresh_token
from app.models.user import User
from jose import JWTError
from app.models.refresh_token import RefreshToken
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr
from sqlalchemy.future import select
from app.core.security import hash_password, verify_password, create_password_reset_token, create_email_verification_token
from app.services.email_service import send_password_reset_email, send_verification_email
from app.core.config import is_mail_configured

logger = logging.getLogger(__name__)

# Gmail / Google Workspace rejected MAIL_USERNAME + MAIL_PASSWORD (App Password, etc.).
_SMTP_AUTH_503_DETAIL = (
    "Mail server rejected SMTP login (535). Use a Google App Password with 2-Step Verification, "
    "and set MAIL_USERNAME and MAIL_FROM to the same mailbox. "
    "https://support.google.com/mail/?p=BadCredentials"
)
# Other SMTP / TLS / network issues from the mail client.
_SMTP_GENERIC_503_DETAIL = (
    "Email could not be sent via SMTP. Check MAIL_* variables, network, and container logs."
)


def _is_smtp_send_failure(exc: BaseException) -> bool:
    """True if this looks like a fastapi-mail / aiosmtplib send failure (not app bugs)."""
    if isinstance(exc, ConnectionErrors):
        return True
    t = type(exc)
    if t.__name__ == "ConnectionErrors" and str(getattr(t, "__module__", "")).startswith(
        "fastapi_mail"
    ):
        return True
    try:
        from aiosmtplib.errors import SMTPAuthenticationError

        if isinstance(exc, SMTPAuthenticationError):
            return True
    except ImportError:
        pass
    blob = str(exc).lower()
    return (
        "535" in blob
        or "badcredentials" in blob
        or "username and password not accepted" in blob
        or "smtpauthenticationerror" in blob
        or "check your credentials or email service configuration" in blob
    )


def _mail_503_detail(exc: BaseException) -> str:
    blob = str(exc)
    if "535" in blob or "BadCredentials" in blob or "Username and Password not accepted" in blob:
        return _SMTP_AUTH_503_DETAIL
    return _SMTP_GENERIC_503_DETAIL


router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

_MAIL_NOT_CONFIGURED_DETAIL = (
    "Email is not configured on the server. Set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_FROM "
    "(and optionally MAIL_SERVER, MAIL_PORT). For Gmail use an App Password and set MAIL_FROM "
    "to the same address as MAIL_USERNAME."
)


@router.post("/signup", response_model=UserProfile)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    db_user = await create_user(
        db,
        user.email,
        user.password,
        first_name=user.first_name,
        last_name=user.last_name,
        phone_number=user.phone_number,
    )
    return db_user

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

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    if not is_mail_configured():
        logger.error("forgot-password called but mail is not configured")
        raise HTTPException(status_code=503, detail=_MAIL_NOT_CONFIGURED_DETAIL)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    token = create_password_reset_token(data.email)
    try:
        await send_password_reset_email(data.email, token)
    except RuntimeError as exc:
        logger.exception("Mail configuration error (password reset) for %s", data.email)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        if not _is_smtp_send_failure(exc):
            raise
        logger.exception("SMTP failed (password reset) for %s", data.email)
        raise HTTPException(status_code=503, detail=_mail_503_detail(exc)) from exc
    return {"message": "Password reset email sent"}

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if payload.get("type") != "password_reset":
        raise HTTPException(status_code=400, detail="Invalid token type")

    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.hashed_password = hash_password(data.new_password)
    db.add(user)
    await db.commit()
    return {"message": "Password reset successfully"}

class SendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/send-verification")
async def send_verification(data: SendVerificationRequest, db: AsyncSession = Depends(get_db)):
    if not is_mail_configured():
        logger.error("send-verification called but mail is not configured")
        raise HTTPException(status_code=503, detail=_MAIL_NOT_CONFIGURED_DETAIL)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    token = create_email_verification_token(data.email)
    try:
        await send_verification_email(data.email, token)
    except RuntimeError as exc:
        logger.exception("Mail configuration error (verification) for %s", data.email)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        if not _is_smtp_send_failure(exc):
            raise
        logger.exception("SMTP failed (verification) for %s", data.email)
        raise HTTPException(status_code=503, detail=_mail_503_detail(exc)) from exc
    return {"message": "Verification email sent"}

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/verify-email")
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.token)
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired verification token")

    if payload.get("type") != "email_verification":
        raise HTTPException(status_code=400, detail="Invalid token type")

    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_verified:
        raise HTTPException(status_code=400, detail="Email already verified")

    user.is_verified = True
    db.add(user)
    await db.commit()
    return {"message": "Email verified successfully"}

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
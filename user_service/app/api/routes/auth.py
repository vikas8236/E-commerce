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
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from app.core.security import hash_password, verify_password, create_password_reset_token, create_email_verification_token
from app.services.email_service import send_password_reset_email, send_verification_email
from app.services.auth_claims import build_access_token_claims
from app.core.config import is_mail_configured
from app.schemas.responses import (
    LoginSuccessResponse,
    MessageResponse,
    RefreshSuccessResponse,
    SignupSuccessResponse,
)

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


@router.post("/signup", response_model=SignupSuccessResponse)
async def signup(user: UserCreate, db: AsyncSession = Depends(get_db)):
    try:
        db_user = await create_user(
            db,
            user.email,
            user.password,
            first_name=user.first_name,
            last_name=user.last_name,
            phone_number=user.phone_number,
        )
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="An account with this email or phone number is already registered. Try signing in or use different details.",
        )
    return SignupSuccessResponse(user=UserProfile.model_validate(db_user))

@router.post("/login", response_model=LoginSuccessResponse)
async def login(user: UserLogin, db: AsyncSession = Depends(get_db)):
    db_user = await authenticate_user(db, user.email, user.password)
    if not db_user:
        raise HTTPException(
            status_code=401,
            detail="The email or password you entered is incorrect. Please try again.",
        )
    # TODO: enable once email verification is implemented
    # if not db_user.is_verified:
    #     raise HTTPException(status_code=401, detail="Email not verified")

    claims = await build_access_token_claims(db, db_user)
    access_token = create_access_token(claims)
    refresh_token = create_refresh_token({"sub": db_user.email})

    db_token = RefreshToken(
        user_id=db_user.id,
        token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(days=7)
    )
    db.add(db_token)
    await db.commit()
    return LoginSuccessResponse(access_token=access_token, refresh_token=refresh_token)

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

@router.post("/change-password", response_model=MessageResponse)
async def change_password(data: ChangePasswordRequest, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):

    if not verify_password(data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="The current password you entered is incorrect. Please try again.",
        )
    current_user.hashed_password = hash_password(data.new_password)
    db.add(current_user)
    await db.commit()
    return MessageResponse(message="Your password was changed successfully.")

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(data: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    if not is_mail_configured():
        logger.error("forgot-password called but mail is not configured")
        raise HTTPException(status_code=503, detail=_MAIL_NOT_CONFIGURED_DETAIL)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account is registered with this email address.",
        )

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
    return MessageResponse(
        message="A password reset link has been sent to your email. It expires in one hour. Check your spam folder if you do not see it.",
    )

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(data: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.token)
    except JWTError:
        raise HTTPException(
            status_code=400,
            detail="This password reset link is invalid or has expired. Please request a new one from the forgot password page.",
        )

    if payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=400,
            detail="This link cannot be used to reset your password. Please use the link from your reset email.",
        )

    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="We could not find the account for this reset link. Please request a new password reset.",
        )

    user.hashed_password = hash_password(data.new_password)
    db.add(user)
    await db.commit()
    return MessageResponse(message="Your password was reset successfully. You can sign in with your new password.")

class SendVerificationRequest(BaseModel):
    email: EmailStr

@router.post("/send-verification", response_model=MessageResponse)
async def send_verification(data: SendVerificationRequest, db: AsyncSession = Depends(get_db)):
    if not is_mail_configured():
        logger.error("send-verification called but mail is not configured")
        raise HTTPException(status_code=503, detail=_MAIL_NOT_CONFIGURED_DETAIL)

    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="No account is registered with this email address.",
        )
    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="This email address is already verified. You can sign in normally.",
        )

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
    return MessageResponse(
        message="A verification email has been sent. Open the link in that email to verify your address.",
    )

class VerifyEmailRequest(BaseModel):
    token: str

@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(data: VerifyEmailRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(data.token)
    except JWTError:
        raise HTTPException(
            status_code=400,
            detail="This verification link is invalid or has expired. Please request a new verification email.",
        )

    if payload.get("type") != "email_verification":
        raise HTTPException(
            status_code=400,
            detail="This link cannot be used to verify your email. Please use the link from your verification email.",
        )

    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="We could not find the account for this verification link.",
        )
    if user.is_verified:
        raise HTTPException(
            status_code=400,
            detail="This email address is already verified.",
        )

    user.is_verified = True
    db.add(user)
    await db.commit()
    return MessageResponse(message="Your email address was verified successfully. Thank you.")

class LogoutRequest(BaseModel):
    refresh_token: str


@router.post("/logout", response_model=MessageResponse)
async def logout(
    data: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.token == data.refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()
    if not db_token:
        raise HTTPException(
            status_code=400,
            detail="This refresh token is not valid for your account, or it was already used. Try signing out from all devices if the problem continues.",
        )
    db_token.is_revoked = True
    db.add(db_token)
    await db.commit()
    return MessageResponse(message="You have been signed out on this device successfully.")

@router.post("/logout-all", response_model=MessageResponse)
async def logout_all(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RefreshToken).where(
        RefreshToken.user_id == current_user.id
    ))
    db_tokens = result.scalars().all()
    for db_token in db_tokens:
        db_token.is_revoked = True
        db.add(db_token)
    await db.commit()
    return MessageResponse(message="You were signed out on all devices where you had an active session.")

class RefreshTokenRequest(BaseModel):
    refresh_token: str


@router.post("/refresh", response_model=RefreshSuccessResponse)
async def refresh(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    refresh_token = data.refresh_token
    try:
        payload = decode_token(refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Your refresh token is invalid or has expired. Please sign in again.",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=401,
            detail="This token cannot be used to refresh your session. Please sign in again.",
        )

    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token == refresh_token,
            RefreshToken.is_revoked == False,
        )
    )
    db_token = result.scalar_one_or_none()

    if not db_token:
        raise HTTPException(
            status_code=401,
            detail="This session is no longer valid. It may have been signed out elsewhere. Please sign in again.",
        )
    if db_token.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=401,
            detail="Your session has expired. Please sign in again.",
        )
    result = await db.execute(select(User).where(User.email == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=401,
            detail="We could not find your account. Please sign in again or create a new account.",
        )

    db_token.is_revoked = True

    claims = await build_access_token_claims(db, user)
    new_access_token = create_access_token(claims)
    new_refresh_token = create_refresh_token({"sub": payload["sub"]})

    db.add(
        RefreshToken(
            user_id=user.id,
            token=new_refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
    )
    await db.commit()

    return RefreshSuccessResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )
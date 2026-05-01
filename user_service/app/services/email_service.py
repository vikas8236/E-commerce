import logging

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig, MessageType

from app.core.config import (
    FRONTEND_URL,
    MAIL_DEBUG,
    MAIL_FROM,
    MAIL_FROM_NAME,
    MAIL_PASSWORD,
    MAIL_PORT,
    MAIL_SERVER,
    MAIL_SSL_TLS,
    MAIL_STARTTLS,
    MAIL_USERNAME,
    is_mail_configured,
)

logger = logging.getLogger(__name__)


def _connection_config() -> ConnectionConfig:
    if not is_mail_configured():
        raise RuntimeError(
            "Mail is not configured. Set MAIL_USERNAME, MAIL_PASSWORD, and MAIL_FROM in the environment."
        )
    return ConnectionConfig(
        MAIL_USERNAME=MAIL_USERNAME,
        MAIL_PASSWORD=MAIL_PASSWORD,
        MAIL_FROM=MAIL_FROM,
        MAIL_FROM_NAME=MAIL_FROM_NAME,
        MAIL_PORT=MAIL_PORT,
        MAIL_SERVER=MAIL_SERVER,
        MAIL_STARTTLS=MAIL_STARTTLS,
        MAIL_SSL_TLS=MAIL_SSL_TLS,
        MAIL_DEBUG=MAIL_DEBUG,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


_fm: FastMail | None = None


def _get_fast_mail() -> FastMail:
    global _fm
    if _fm is None:
        _fm = FastMail(_connection_config())
    return _fm


async def send_password_reset_email(email: str, token: str):
    reset_link = f"{FRONTEND_URL}/reset-password?token={token}"
    html = f"""
    <h2>Password Reset Request</h2>
    <p>You requested to reset your password. Click the link below to set a new password:</p>
    <p><a href="{reset_link}" style="padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 5px;">Reset Password</a></p>
    <p>This link will expire in 1 hour.</p>
    <p>If you didn't request this, you can safely ignore this email.</p>
    """

    message = MessageSchema(
        subject="Reset Your Password",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    try:
        logger.info("Sending password reset email to %s", email)
        await _get_fast_mail().send_message(message)
    except Exception:
        logger.exception("SMTP send failed (password reset) to %s", email)
        raise
    logger.info("Password reset email accepted by SMTP for %s", email)


async def send_verification_email(email: str, token: str):
    verify_link = f"{FRONTEND_URL}/verify-email?token={token}"
    html = f"""
    <h2>Verify Your Email</h2>
    <p>Thanks for signing up! Please verify your email address by clicking the link below:</p>
    <p><a href="{verify_link}" style="padding: 10px 20px; background-color: #28a745; color: white; text-decoration: none; border-radius: 5px;">Verify Email</a></p>
    <p>This link will expire in 24 hours.</p>
    """

    message = MessageSchema(
        subject="Verify Your Email Address",
        recipients=[email],
        body=html,
        subtype=MessageType.html,
    )
    try:
        logger.info("Sending verification email to %s", email)
        await _get_fast_mail().send_message(message)
    except Exception:
        logger.exception("SMTP send failed (verification) to %s", email)
        raise
    logger.info("Verification email accepted by SMTP for %s", email)

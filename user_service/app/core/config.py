import os
from pathlib import Path

from dotenv import load_dotenv

# Load user_service/.env even when the process cwd is the monorepo root.
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
# Gmail app passwords are often pasted with spaces; SMTP expects the 16-char secret.
_raw_mail_password = os.getenv("MAIL_PASSWORD")
MAIL_PASSWORD = _raw_mail_password.replace(" ", "") if _raw_mail_password else None
MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "E-Commerce App")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", "587"))
# Port 587: STARTTLS (defaults). Port 465: set MAIL_SSL_TLS=true and MAIL_STARTTLS=false.
MAIL_STARTTLS = os.getenv("MAIL_STARTTLS", "true").lower() in ("1", "true", "yes")
MAIL_SSL_TLS = os.getenv("MAIL_SSL_TLS", "false").lower() in ("1", "true", "yes")
# Set MAIL_DEBUG=1 to print SMTP traffic to logs (troubleshooting only).
MAIL_DEBUG = int(os.getenv("MAIL_DEBUG", "0"))
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


def is_mail_configured() -> bool:
    return bool(MAIL_USERNAME and MAIL_PASSWORD and MAIL_FROM)
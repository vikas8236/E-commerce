import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://catalog:catalog@localhost:5433/catalog_db",
)

SECRET_KEY = os.getenv("SECRET_KEY", "lRdiT9UWbqiV6nkxgzPgiQKeLI7wLBISP_a6dknBkumZlF0LU-GiGuh7MZ2ruc2kMkel66Kl1jo6r-N753nkzA")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
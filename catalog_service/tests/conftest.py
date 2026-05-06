import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine

import app.models.category  # noqa: F401
import app.models.product  # noqa: F401
import app.models.product_category  # noqa: F401
import app.models.product_image  # noqa: F401
from app.main import app


@pytest.fixture
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_engine):
    with TestClient(app) as c:
        yield c

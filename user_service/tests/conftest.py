"""
Pytest imports `conftest.py` before test modules.

We set DATABASE_URL / SECRET_KEY here so `app.db.session` builds the engine with
SQLite before any test file does `from app.main import app`.

Use the `client` fixture for API tests that need a fresh DB (tables created per test).
"""

from __future__ import annotations

import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite://"
os.environ["SECRET_KEY"] = "lRdiT9UWbqiV6nkxgzPgiQKeLI7wLBISP_a6dknBkumZlF0LU-GiGuh7MZ2ruc2kMkel66Kl1jo6r-N753nkzA"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import AsyncSessionLocal, engine
from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permissions import RolePermission

# Register models on Base.metadata before create_all
import app.models.address  
import app.models.permission  
import app.models.refresh_token  
import app.models.role  
import app.models.role_permissions  
import app.models.user  
import app.models.user_role  

from app.main import app


@pytest.fixture
async def db_engine():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed minimal RBAC defaults used by route-level permission checks.
    async with AsyncSessionLocal() as db:
        customer = Role(name="customer", description="Customer role")
        seller = Role(name="seller", description="Seller role")
        support = Role(name="support", description="Support role")
        admin = Role(name="admin", description="Admin role")
        db.add_all([customer, seller, support, admin])
        await db.flush()

        permissions = [
            Permission(name="users:read_self", description="Read own user profile."),
            Permission(name="users:update_self", description="Update own user profile."),
            Permission(name="addresses:read_self", description="Read own saved addresses."),
            Permission(name="addresses:write_self", description="Create, update, and delete own addresses."),
            Permission(name="users:manage_roles", description="Assign and revoke user roles."),
        ]
        db.add_all(permissions)
        await db.flush()

        customer_permission_names = {
            "users:read_self",
            "users:update_self",
            "addresses:read_self",
            "addresses:write_self",
        }
        db.add_all(
            [
                RolePermission(role_id=customer.id, permission_id=permission.id)
                for permission in permissions
                if permission.name in customer_permission_names
            ]
        )
        db.add_all(
            [
                RolePermission(role_id=seller.id, permission_id=permission.id)
                for permission in permissions
                if permission.name in customer_permission_names
            ]
        )
        db.add_all(
            [
                RolePermission(role_id=support.id, permission_id=permission.id)
                for permission in permissions
                if permission.name == "users:read_self"
            ]
        )
        db.add_all(
            [
                RolePermission(role_id=admin.id, permission_id=permission.id)
                for permission in permissions
            ]
        )
        await db.commit()

    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client(db_engine):
    """HTTP client against the app; database is empty except what the test inserts."""
    with TestClient(app) as c:
        yield c

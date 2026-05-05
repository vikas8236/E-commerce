"""
Start here, then add cases yourself (duplicate signup, wrong password, refresh, logout, …).

Use the `client` fixture from conftest so each test gets a clean DB. Do not create a
module-level TestClient or import `app` here — that can run before conftest sets env/DB.

Import `auth_headers` from `tests.helpers` for protected routes.
"""

from tests.helpers import auth_headers
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import AsyncSessionLocal
from app.api.deps import get_current_user_permissions
from app.models.role import Role
from app.models.user import User


async def test_signup_returns_user_profile(client):
    payload = {
        "email": "ada@example.com",
        "password": "a-secure-password-here",
        "first_name": "Ada",
        "last_name": "Lovelace",
    }
    response = client.post("/auth/signup", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == payload["email"]
    assert body["user"]["first_name"] == payload["first_name"]
    assert "id" in body["user"]


async def test_login_returns_tokens_after_signup(client):
    email = "bob@example.com"
    password = "another-secure-password"
    client.post("/auth/signup", json={"email": email, "password": password})
    response = client.post("/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data and "refresh_token" in data


async def test_get_user_profile(client):
    email = "carol@example.com"
    password = "password-for-carol"
    client.post("/auth/signup", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    response = client.get("/users/me", headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["user"]["email"] == email


async def test_signup_assigns_default_customer_role(client):
    email = "role-check@example.com"
    password = "role-check-password"
    response = client.post("/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.email == email)
        )
        user = result.scalar_one()
        assert any(role.name == "customer" for role in user.roles)


async def test_get_user_profile_forbidden_without_permission(client):
    email = "no-perm@example.com"
    password = "no-perm-password"
    client.post("/auth/signup", json={"email": email, "password": password})
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    async def deny_permissions_override() -> set[str]:
        return set()

    client.app.dependency_overrides[get_current_user_permissions] = deny_permissions_override
    try:
        response = client.get("/users/me", headers=auth_headers(token))
        assert response.status_code == 403
        assert "Missing permissions" in response.json()["detail"]
    finally:
        client.app.dependency_overrides.pop(get_current_user_permissions, None)


async def test_non_admin_cannot_list_user_roles(client):
    email = "customer-only@example.com"
    password = "customer-only-password"
    signup = client.post("/auth/signup", json={"email": email, "password": password})
    user_id = signup.json()["user"]["id"]
    login = client.post("/auth/login", json={"email": email, "password": password})
    token = login.json()["access_token"]

    response = client.get(f"/users/{user_id}/roles", headers=auth_headers(token))
    assert response.status_code == 403


async def test_admin_can_assign_list_and_revoke_user_roles(client):
    target_signup = client.post(
        "/auth/signup",
        json={"email": "target@example.com", "password": "target-password"},
    )
    target_user_id = target_signup.json()["user"]["id"]

    admin_email = "admin@example.com"
    admin_password = "admin-password"
    admin_signup = client.post(
        "/auth/signup",
        json={"email": admin_email, "password": admin_password},
    )
    admin_user_id = admin_signup.json()["user"]["id"]

    async with AsyncSessionLocal() as db:
        user_result = await db.execute(
            select(User).options(selectinload(User.roles)).where(User.id == admin_user_id)
        )
        admin_user = user_result.scalar_one()
        role_result = await db.execute(select(Role).where(Role.name == "admin"))
        admin_role = role_result.scalar_one()
        if admin_role not in admin_user.roles:
            admin_user.roles.append(admin_role)
            db.add(admin_user)
            await db.commit()

    admin_login = client.post(
        "/auth/login",
        json={"email": admin_email, "password": admin_password},
    )
    admin_token = admin_login.json()["access_token"]
    headers = auth_headers(admin_token)

    assign = client.post(
        f"/users/{target_user_id}/roles",
        json={"role": "seller"},
        headers=headers,
    )
    assert assign.status_code == 200
    assert "seller" in assign.json()["roles"]

    list_after_assign = client.get(f"/users/{target_user_id}/roles", headers=headers)
    assert list_after_assign.status_code == 200
    assert "customer" in list_after_assign.json()["roles"]
    assert "seller" in list_after_assign.json()["roles"]

    revoke = client.delete(f"/users/{target_user_id}/roles/seller", headers=headers)
    assert revoke.status_code == 200
    assert "seller" not in revoke.json()["roles"]

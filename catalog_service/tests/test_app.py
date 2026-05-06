from app.api.deps import get_current_user_permissions
from app.core.security import create_access_token


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_products_list_initially_empty(client):
    response = client.get("/products/")
    assert response.status_code == 200
    body = response.json()
    assert body["products"] == []


def test_create_product_requires_auth(client):
    payload = {
        "seller_id": 1,
        "name": "Sample Product",
        "slug": "sample-product",
        "sku": "SKU-SAMPLE-001",
        "description": "demo",
        "price": 10.5,
        "currency": "USD",
        "status": "draft",
        "is_active": True,
        "category_ids": [],
    }
    response = client.post("/products/", json=payload)
    assert response.status_code == 401


def test_create_product_forbidden_without_permission(client):
    token = create_access_token({"sub": "seller@example.com", "roles": ["seller"], "permissions": []})

    async def deny_permissions() -> set[str]:
        return set()

    payload = {
        "seller_id": 1,
        "name": "Denied Product",
        "slug": "denied-product",
        "sku": "SKU-DENY-001",
        "description": "demo",
        "price": 12.5,
        "currency": "USD",
        "status": "draft",
        "is_active": True,
        "category_ids": [],
    }
    client.app.dependency_overrides[get_current_user_permissions] = deny_permissions
    try:
        response = client.post("/products/", json=payload, headers=auth_headers(token))
        assert response.status_code == 403
    finally:
        client.app.dependency_overrides.pop(get_current_user_permissions, None)


def test_create_product_allowed_with_permission(client):
    token = create_access_token(
        {
            "sub": "seller@example.com",
            "roles": ["seller"],
            "permissions": ["catalog:products:write"],
        }
    )

    payload = {
        "seller_id": 7,
        "name": "Allowed Product",
        "slug": "allowed-product",
        "sku": "SKU-ALLOW-001",
        "description": "demo",
        "price": 15.0,
        "currency": "USD",
        "status": "draft",
        "is_active": True,
        "category_ids": [],
    }
    response = client.post("/products/", json=payload, headers=auth_headers(token))
    assert response.status_code == 200
    assert response.json()["product"]["slug"] == "allowed-product"


def test_create_category_requires_permission(client):
    token = create_access_token(
        {
            "sub": "seller@example.com",
            "roles": ["seller"],
            "permissions": ["catalog:products:write"],
        }
    )
    response = client.post(
        "/categories/",
        json={"name": "Games", "slug": "games", "parent_id": None, "is_active": True},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


def test_create_category_allowed_for_admin(client):
    token = create_access_token(
        {
            "sub": "admin@example.com",
            "roles": ["admin"],
            "permissions": [],
        }
    )
    response = client.post(
        "/categories/",
        json={"name": "Appliances", "slug": "appliances", "parent_id": None, "is_active": True},
        headers=auth_headers(token),
    )
    assert response.status_code == 200
    assert response.json()["category"]["slug"] == "appliances"

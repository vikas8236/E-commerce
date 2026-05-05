"""Small helpers for API tests; import these from your test modules."""


def auth_headers(access_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token}"}

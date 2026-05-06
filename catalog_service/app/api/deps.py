from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import JWTError, decode_token

security = HTTPBearer(auto_error=False)


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict:
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Provide a Bearer access token.",
        )

    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Your access token is invalid or has expired. Please sign in again.",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=401,
            detail="This token cannot be used here. Please use a valid access token.",
        )
    return payload


async def get_current_user_permissions(
    token_data: dict = Depends(get_current_user_token),
) -> set[str]:
    permissions = token_data.get("permissions", [])
    if not isinstance(permissions, list):
        permissions = []
    return set(permissions)


async def get_current_user_roles(
    token_data: dict = Depends(get_current_user_token),
) -> set[str]:
    roles = token_data.get("roles", [])
    if not isinstance(roles, list):
        roles = []
    return set(roles)


def require_permissions(*required_permissions: str):
    required = set(required_permissions)

    async def _permission_checker(
        user_permissions: set[str] = Depends(get_current_user_permissions),
        user_roles: set[str] = Depends(get_current_user_roles),
    ) -> None:
        if "admin" in user_roles:
            return
        missing = sorted(required - user_permissions)
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to perform this action. Missing permissions: {', '.join(missing)}",
            )

    return _permission_checker

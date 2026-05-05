from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.future import select

from app.core.security import decode_token
from app.db.session import AsyncSessionLocal
from app.models.permission import Permission
from app.models.role_permissions import RolePermission
from app.models.user import User
from app.models.user_role import UserRole

security = HTTPBearer()


def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
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


async def get_current_user(
    token_data: dict = Depends(get_current_user_token),
):
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(User).where(User.email == token_data["sub"])
        )
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=404,
                detail="We could not find your account. It may have been removed.",
            )

        return user


async def get_current_user_permissions(
    token_data: dict = Depends(get_current_user_token),
) -> set[str]:
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User.id).where(User.email == token_data["sub"]))
        user_id = result.scalar_one_or_none()
        if not user_id:
            raise HTTPException(
                status_code=404,
                detail="We could not find your account. It may have been removed.",
            )

        permission_result = await db.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(UserRole, UserRole.role_id == RolePermission.role_id)
            .where(UserRole.user_id == user_id)
        )
        return set(permission_result.scalars().all())


def require_permissions(*required_permissions: str):
    required = set(required_permissions)

    async def _permission_checker(
        user_permissions: set[str] = Depends(get_current_user_permissions),
    ) -> None:
        missing = sorted(required - user_permissions)
        if missing:
            raise HTTPException(
                status_code=403,
                detail=f"You do not have permission to perform this action. Missing permissions: {', '.join(missing)}",
            )

    return _permission_checker
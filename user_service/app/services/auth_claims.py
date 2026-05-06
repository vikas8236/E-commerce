"""Claims embedded in access tokens for downstream services (e.g. catalog RBAC)."""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models.role import Role
from app.models.user import User


async def build_access_token_claims(db: AsyncSession, user: User) -> dict:
    """Load roles + flattened permissions and return JWT payload fields (besides type/exp)."""
    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions))
        .where(User.id == user.id)
    )
    u = result.scalar_one()
    roles = sorted({r.name for r in u.roles})
    permissions: set[str] = set()
    for role in u.roles:
        for perm in role.permissions:
            permissions.add(perm.name)
    return {
        "sub": u.email,
        "user_id": u.id,
        "roles": roles,
        "permissions": sorted(permissions),
    }

from app.models.user import User
from app.models.role import Role
from app.core.security import hash_password, verify_password
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_ROLE_NAME = "customer"


async def create_user(
    db: AsyncSession,
    email: str,
    password: str,
    *,
    first_name: str | None = None,
    last_name: str | None = None,
    phone_number: str | None = None,
):
    user = User(
        email=email,
        hashed_password=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        phone_number=phone_number,
    )
    # Ensure every new account gets the default RBAC role.
    result = await db.execute(select(Role).where(Role.name == DEFAULT_ROLE_NAME))
    default_role = result.scalar_one_or_none()
    if default_role is None:
        default_role = Role(
            name=DEFAULT_ROLE_NAME,
            description="Default role assigned at signup.",
        )
        db.add(default_role)
        await db.flush()
    user.roles.append(default_role)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def authenticate_user(db: AsyncSession, email: str, password: str):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
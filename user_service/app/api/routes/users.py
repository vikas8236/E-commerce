from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.api.deps import get_current_user, require_permissions
from app.models.role import Role
from app.models.user import User
from app.schemas.responses import UserMeResponse, UserRolesResponse
from app.schemas.user import UserProfile, UserProfileUpdate
from app.db.session import AsyncSession, AsyncSessionLocal

router = APIRouter()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


class AssignRoleRequest(BaseModel):
    role: str


@router.get("/me", response_model=UserMeResponse)
async def get_user_profile(
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("users:read_self")),
):
    return UserMeResponse(
        message="Your profile was loaded successfully.",
        user=UserProfile.model_validate(current_user),
    )


@router.put("/me", response_model=UserMeResponse)
async def update_user_profile(
    user_profile: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    _: None = Depends(require_permissions("users:update_self")),
    db: AsyncSession = Depends(get_db),
):
    for field, value in user_profile.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    db.add(current_user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="That phone number is already registered to another account. Please use a different number.",
        )
    await db.refresh(current_user)
    return UserMeResponse(
        message="Your profile was updated successfully.",
        user=UserProfile.model_validate(current_user),
    )


@router.get("/{user_id}/roles", response_model=UserRolesResponse)
async def list_user_roles(
    user_id: int,
    _: None = Depends(require_permissions("users:manage_roles")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    roles = sorted(role.name for role in user.roles)
    return UserRolesResponse(
        message="User roles loaded successfully.",
        user_id=user.id,
        roles=roles,
    )


@router.post("/{user_id}/roles", response_model=UserRolesResponse)
async def assign_role(
    user_id: int,
    payload: AssignRoleRequest,
    _: None = Depends(require_permissions("users:manage_roles")),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    role_result = await db.execute(select(Role).where(Role.name == payload.role))
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found.")

    if role not in user.roles:
        user.roles.append(role)
        db.add(user)
        await db.commit()
        await db.refresh(user)

    return UserRolesResponse(
        message=f"Role '{payload.role}' is assigned to user {user.id}.",
        user_id=user.id,
        roles=sorted(role.name for role in user.roles),
    )


@router.delete("/{user_id}/roles/{role_name}", response_model=UserRolesResponse)
async def revoke_role(
    user_id: int,
    role_name: str,
    _: None = Depends(require_permissions("users:manage_roles")),
    db: AsyncSession = Depends(get_db),
):
    user_result = await db.execute(
        select(User).options(selectinload(User.roles)).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    role_to_remove = next((role for role in user.roles if role.name == role_name), None)
    if role_to_remove is None:
        raise HTTPException(
            status_code=404,
            detail=f"Role '{role_name}' is not assigned to this user.",
        )

    user.roles.remove(role_to_remove)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserRolesResponse(
        message=f"Role '{role_name}' was revoked from user {user.id}.",
        user_id=user.id,
        roles=sorted(role.name for role in user.roles),
    )

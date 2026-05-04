from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.address import AddressCreate, AddressResponse, AddressUpdate
from app.schemas.responses import AddressListResponse, AddressMutationResponse, MessageResponse
from app.models.address import Address
from app.db.session import AsyncSession, AsyncSessionLocal

router = APIRouter()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@router.get("/", response_model=AddressListResponse)
async def get_addresses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()
    count = len(addresses)
    if count == 0:
        msg = "You have no saved addresses yet. Add one when you check out or from your account settings."
    else:
        msg = f"Retrieved {count} saved address{'es' if count != 1 else ''}."
    return AddressListResponse(
        message=msg,
        addresses=[AddressResponse.model_validate(a) for a in addresses],
    )


@router.post("/", response_model=AddressMutationResponse)
async def create_address(
    address: AddressCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    new_address = Address(user_id=current_user.id, **address.model_dump())
    db.add(new_address)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This address could not be saved because it conflicts with existing data. Please check your input.",
        )
    await db.refresh(new_address)
    return AddressMutationResponse(
        message="Your new address was saved successfully.",
        address=AddressResponse.model_validate(new_address),
    )


@router.put("/{address_id}", response_model=AddressMutationResponse)
async def update_address(
    address_id: int,
    address: AddressUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Address).where(Address.id == address_id, Address.user_id == current_user.id)
    )
    db_address = result.scalar_one_or_none()
    if not db_address:
        raise HTTPException(
            status_code=404,
            detail="We could not find that address on your account. It may have been deleted.",
        )
    for field, value in address.model_dump(exclude_unset=True).items():
        setattr(db_address, field, value)
    db.add(db_address)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="This address could not be updated because something conflicts with your other saved data. Please check your input.",
        )
    await db.refresh(db_address)
    return AddressMutationResponse(
        message="Your address was updated successfully.",
        address=AddressResponse.model_validate(db_address),
    )


@router.delete("/{address_id}", response_model=MessageResponse)
async def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Address).where(Address.id == address_id, Address.user_id == current_user.id)
    )
    db_address = result.scalar_one_or_none()
    if not db_address:
        raise HTTPException(
            status_code=404,
            detail="We could not find that address on your account. It may have already been removed.",
        )
    await db.execute(
        delete(Address).where(
            Address.id == address_id,
            Address.user_id == current_user.id,
        )
    )
    await db.commit()
    return MessageResponse(message="That address was removed from your account successfully.")

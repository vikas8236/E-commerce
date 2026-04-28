from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.address import AddressCreate, AddressUpdate
from app.models.address import Address
from app.db.session import AsyncSession, AsyncSessionLocal
from sqlalchemy.future import select

router = APIRouter()

async def get_db():
    async with AsyncSessionLocal() as db:
        yield db

@router.get("/")
async def get_addresses(current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.user_id == current_user.id))
    addresses = result.scalars().all()
    return addresses

@router.post("/")
async def create_address(address: AddressCreate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    new_address = Address(user_id=current_user.id, **address.model_dump())
    db.add(new_address)
    await db.commit()
    await db.refresh(new_address)
    return new_address

@router.put("/{address_id}")
async def update_address(address_id: int, address: AddressUpdate, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.id == address_id, Address.user_id == current_user.id))
    db_address = result.scalar_one_or_none()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    for field, value in address.model_dump(exclude_unset=True).items():
        setattr(db_address, field, value)
    db.add(db_address)
    await db.commit()
    await db.refresh(db_address)
    return db_address

@router.delete("/{address_id}")
async def delete_address(address_id: int, current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Address).where(Address.id == address_id, Address.user_id == current_user.id))
    db_address = result.scalar_one_or_none()
    if not db_address:
        raise HTTPException(status_code=404, detail="Address not found")
    await db.delete(db_address)
    await db.commit()
    return {"message": "Address deleted successfully"}
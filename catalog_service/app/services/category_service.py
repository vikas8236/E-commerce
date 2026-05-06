from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.category import Category
from app.schemas.category import CategoryCreate


async def list_categories(db: AsyncSession) -> list[Category]:
    result = await db.execute(select(Category).order_by(Category.id.desc()))
    return list(result.scalars().all())


async def create_category(db: AsyncSession, payload: CategoryCreate) -> Category:
    category = Category(**payload.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category

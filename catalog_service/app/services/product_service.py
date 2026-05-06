from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.category import Category
from app.models.product import Product
from app.schemas.product import ProductCreate


async def list_products(db: AsyncSession) -> list[Product]:
    result = await db.execute(select(Product).order_by(Product.id.desc()))
    return list(result.scalars().all())


async def create_product(db: AsyncSession, payload: ProductCreate) -> Product:
    data = payload.model_dump(exclude={"category_ids"})
    product = Product(**data)

    if payload.category_ids:
        category_result = await db.execute(
            select(Category).where(Category.id.in_(payload.category_ids))
        )
        categories = list(category_result.scalars().all())
        product.categories = categories

    db.add(product)
    await db.commit()
    await db.refresh(product)
    return product

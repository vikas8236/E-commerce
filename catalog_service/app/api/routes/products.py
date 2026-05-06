from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permissions
from app.db.session import AsyncSessionLocal
from app.schemas.product import ProductCreate, ProductOut
from app.schemas.responses import ProductListResponse, ProductMutationResponse
from app.services.product_service import create_product, list_products

router = APIRouter()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@router.get("/", response_model=ProductListResponse)
async def get_products(db: AsyncSession = Depends(get_db)):
    products = await list_products(db)
    return ProductListResponse(products=[ProductOut.model_validate(p) for p in products])


@router.post("/", response_model=ProductMutationResponse)
async def post_product(
    payload: ProductCreate,
    _: None = Depends(require_permissions("catalog:products:write")),
    db: AsyncSession = Depends(get_db),
):
    product = await create_product(db, payload)
    return ProductMutationResponse(
        message="Product created successfully.",
        product=ProductOut.model_validate(product),
    )

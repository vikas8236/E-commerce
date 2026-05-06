from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permissions
from app.db.session import AsyncSessionLocal
from app.schemas.category import CategoryCreate, CategoryOut
from app.schemas.responses import CategoryListResponse, CategoryMutationResponse
from app.services.category_service import create_category, list_categories

router = APIRouter()


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


@router.get("/", response_model=CategoryListResponse)
async def get_categories(db: AsyncSession = Depends(get_db)):
    categories = await list_categories(db)
    return CategoryListResponse(categories=[CategoryOut.model_validate(c) for c in categories])


@router.post("/", response_model=CategoryMutationResponse)
async def post_category(
    payload: CategoryCreate,
    _: None = Depends(require_permissions("catalog:categories:write")),
    db: AsyncSession = Depends(get_db),
):
    category = await create_category(db, payload)
    return CategoryMutationResponse(
        message="Category created successfully.",
        category=CategoryOut.model_validate(category),
    )

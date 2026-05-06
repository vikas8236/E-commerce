from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    seller_id: int
    name: str
    slug: str
    sku: str
    description: str | None = None
    price: Decimal = Field(gt=0)
    currency: str = "USD"
    status: str = "draft"
    is_active: bool = True
    category_ids: list[int] = []


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    seller_id: int
    name: str
    slug: str
    sku: str
    description: str | None = None
    price: Decimal
    currency: str
    status: str
    is_active: bool
    created_at: datetime | None = None

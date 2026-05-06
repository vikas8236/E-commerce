from pydantic import BaseModel, Field

from app.schemas.category import CategoryOut
from app.schemas.product import ProductOut


class MessageResponse(BaseModel):
    message: str


class ProductListResponse(BaseModel):
    message: str = Field(default="Products loaded successfully.")
    products: list[ProductOut]


class ProductMutationResponse(BaseModel):
    message: str
    product: ProductOut


class CategoryListResponse(BaseModel):
    message: str = Field(default="Categories loaded successfully.")
    categories: list[CategoryOut]


class CategoryMutationResponse(BaseModel):
    message: str
    category: CategoryOut

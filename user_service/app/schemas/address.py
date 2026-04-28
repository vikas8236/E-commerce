from pydantic import BaseModel
from datetime import datetime
class AddressCreate(BaseModel):
    street: str | None = None
    city: str
    state: str
    zip_code: str
    country: str
    is_default: bool
    
class AddressUpdate(BaseModel):
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip_code: str | None = None
    country: str | None = None
    is_default: bool | None = None

class AddressResponse(BaseModel):
    id: int
    street: str | None = None
    city: str
    state: str
    zip_code: str
    country: str
    is_default: bool
    created_at: datetime
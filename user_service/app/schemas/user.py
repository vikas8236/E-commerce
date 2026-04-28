from pydantic import BaseModel, EmailStr
from datetime import datetime
class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: int
    email: EmailStr
    first_name: str
    last_name: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None

class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from datetime import datetime


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    is_active: bool | None = None
    created_at: datetime | None = None

    @field_validator("is_active", mode="before")
    @classmethod
    def coerce_is_active(cls, v):
        if v is None:
            return None
        return bool(v)

class UserProfileUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None

"""Standard API envelopes so success responses include a clear human-readable message."""

from pydantic import BaseModel, Field

from app.schemas.address import AddressResponse
from app.schemas.user import UserProfile


class MessageResponse(BaseModel):
    message: str


class SignupSuccessResponse(BaseModel):
    message: str = Field(default="Your account was created successfully. You can sign in now.")
    user: UserProfile


class LoginSuccessResponse(BaseModel):
    message: str = Field(
        default="You are signed in. Use the access token in the Authorization header until it expires."
    )
    access_token: str
    refresh_token: str


class RefreshSuccessResponse(BaseModel):
    message: str = Field(default="Your session was refreshed successfully.")
    access_token: str
    refresh_token: str


class UserMeResponse(BaseModel):
    message: str
    user: UserProfile


class AddressListResponse(BaseModel):
    message: str
    addresses: list[AddressResponse]


class AddressMutationResponse(BaseModel):
    message: str
    address: AddressResponse

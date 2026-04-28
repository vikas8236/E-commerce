from fastapi import FastAPI, Depends
from app.api.routes import auth, users, addresses
from app.api.deps import get_current_user

app = FastAPI()

app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(users.router, prefix="/users", dependencies=[Depends(get_current_user)], tags=["Users"])
app.include_router(addresses.router, prefix="/addresses", dependencies=[Depends(get_current_user)], tags=["Addresses"])


from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.api.deps import get_current_user
from app.api.routes import addresses, auth, users

app = FastAPI()


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
):
    return JSONResponse(
        status_code=422,
        content={
            "message": "Some fields in your request are invalid or missing. See 'errors' for details.",
            "errors": exc.errors(),
        },
    )


@app.exception_handler(IntegrityError)
async def integrity_exception_handler(request: Request, exc: IntegrityError):
    return JSONResponse(
        status_code=409,
        content={
            "detail": "This action could not be completed because something you entered already exists or conflicts with another record (for example, a duplicate email or phone number).",
        },
    )


app.include_router(auth.router, prefix="/auth", tags=["Auth"])
app.include_router(
    users.router,
    prefix="/users",
    dependencies=[Depends(get_current_user)],
    tags=["Users"],
)
app.include_router(
    addresses.router,
    prefix="/addresses",
    dependencies=[Depends(get_current_user)],
    tags=["Addresses"],
)

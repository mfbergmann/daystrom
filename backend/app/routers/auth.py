"""Authentication endpoints."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.core.security import create_access_token, hash_pin, verify_pin

router = APIRouter(prefix="/api/auth", tags=["auth"])

# In-memory hash of the configured PIN
_pin_hash: str | None = None


def _get_pin_hash() -> str | None:
    global _pin_hash
    if settings.pin and _pin_hash is None:
        _pin_hash = hash_pin(settings.pin)
    return _pin_hash


class LoginRequest(BaseModel):
    pin: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AuthStatus(BaseModel):
    auth_required: bool


@router.get("/status", response_model=AuthStatus)
async def auth_status():
    """Check if authentication is required."""
    return AuthStatus(auth_required=bool(settings.pin))


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """Authenticate with PIN and receive JWT."""
    if not settings.pin:
        return LoginResponse(access_token=create_access_token())

    pin_hash = _get_pin_hash()
    if not pin_hash or not verify_pin(body.pin, pin_hash):
        raise HTTPException(status_code=401, detail="Invalid PIN")

    return LoginResponse(access_token=create_access_token())

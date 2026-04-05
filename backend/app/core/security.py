from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)

ALGORITHM = "HS256"


def hash_pin(pin: str) -> str:
    return pwd_context.hash(pin)


def verify_pin(plain_pin: str, hashed_pin: str) -> bool:
    return pwd_context.verify(plain_pin, hashed_pin)


def create_access_token() -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    return jwt.encode({"exp": expire, "sub": "user"}, settings.secret_key, algorithm=ALGORITHM)


def _validate_token(token: str) -> bool:
    """Validate a JWT token string. Returns True if valid, raises otherwise."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("sub") != "user":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    return True


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    token: str | None = Query(None),
) -> bool:
    """Authenticate via Bearer header or ?token= query param.

    Query param fallback is needed for EventSource (SSE) which can't set headers.
    """
    if not settings.pin:
        return True

    # Try Bearer header first
    if credentials is not None:
        return _validate_token(credentials.credentials)

    # Fall back to query param (for SSE / EventSource)
    if token is not None:
        return _validate_token(token)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

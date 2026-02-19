"""
FastAPI dependency that protects routes behind JWT authentication.

Usage in a route:
    @router.get("/protected")
    def my_route(username: str = Depends(get_current_user)):
        ...
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.services.auth import decode_access_token

# Tells FastAPI/Swagger where the token endpoint is, enabling the
# "Authorize" button in the interactive docs.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


def get_current_user(token: str = Depends(oauth2_scheme)) -> str:
    """
    Decode the Bearer token and return the authenticated username.

    Raises HTTP 401 if the token is missing, expired, or tampered with.
    Authorization is intentionally open to *all* authenticated users —
    no role or scope checks are performed here.
    """
    username = decode_access_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return username

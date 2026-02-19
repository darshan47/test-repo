"""
Auth router — exposes the /auth/token login endpoint.

Uses OAuth2 "password" grant (RFC 6749 §4.3) so the client sends
  Content-Type: application/x-www-form-urlencoded
  username=<user>&password=<pass>

and receives a bearer token in return.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from app.services.auth import authenticate_user, create_access_token
from app import config

router = APIRouter(prefix="/auth", tags=["Authentication"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Obtain a JWT access token",
    description=(
        "Submit valid credentials to receive a Bearer token. "
        "Pass the token in every subsequent request as "
        "`Authorization: Bearer <token>`."
    ),
)
def login(form_data: OAuth2PasswordRequestForm = Depends()) -> TokenResponse:
    """Validate credentials and issue a JWT."""
    if not authenticate_user(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(subject=form_data.username)
    return TokenResponse(
        access_token=token,
        expires_in=config.JWT_EXPIRE_MINUTES * 60,
    )

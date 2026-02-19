"""
Authentication service: credential validation + JWT creation/verification.

Flow
────
1. Client calls POST /auth/token with username + password (OAuth2 form).
2. We verify the credentials against the demo user store (config.demo_users).
3. On success we return a signed JWT access token.
4. Every subsequent request must supply  Authorization: Bearer <token>.
5. The `get_current_user` dependency decodes and validates the token and
   injects the username into the route handler.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt context for hashing passwords in the demo store
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ── Token helpers ─────────────────────────────────────────────────────────────

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT whose 'sub' claim is *subject* (typically username)."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.jwt_expire_minutes)
    )
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> Optional[str]:
    """
    Decode the JWT and return the username ('sub' claim).
    Returns None if the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload.get("sub")
    except JWTError:
        return None


# ── Credential validation ─────────────────────────────────────────────────────

def authenticate_user(username: str, password: str) -> bool:
    """
    Check *username* / *password* against the configured demo user store.

    The demo store uses plain-text passwords for simplicity; swap this for
    a real user store (e.g. Cognito, RDS) in production.
    """
    users = settings.get_demo_users()
    stored_password = users.get(username)
    if not stored_password:
        return False
    # Accept plain-text comparison (demo) or bcrypt hashes
    if stored_password.startswith("$2b$"):
        return pwd_context.verify(password, stored_password)
    return stored_password == password

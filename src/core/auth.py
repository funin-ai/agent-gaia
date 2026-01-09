"""Authentication module with OAuth and JWT support."""

from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

from jose import JWTError, jwt
from pydantic import BaseModel
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.core.settings import get_settings
from src.utils.logger import logger


# JWT Configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days


class TokenData(BaseModel):
    """JWT token payload data."""
    user_id: str
    email: str
    provider: str  # google, github
    exp: Optional[datetime] = None


class User(BaseModel):
    """User model."""
    id: str
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str  # oauth provider (google, github)
    provider_id: str  # provider's user id
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True


class UserCreate(BaseModel):
    """User creation from OAuth data."""
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None
    provider: str
    provider_id: str


def get_secret_key() -> str:
    """Get JWT secret key from settings or generate one."""
    settings = get_settings()
    # Try to get from vault or config, fallback to generated
    if hasattr(settings, 'auth') and hasattr(settings.auth, 'jwt_secret'):
        return settings.auth.jwt_secret
    # Fallback: use app name + some static string (not ideal for production)
    return f"agent-gaia-secret-{settings.app_version}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token.
    Args:
        data: Payload data to encode
        expires_delta: Token expiration time
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, get_secret_key(), algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Optional[TokenData]:
    """Decode and validate JWT token.
    Args:
        token: JWT token string
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, get_secret_key(), algorithms=[ALGORITHM])
        user_id: str = payload.get("user_id")
        email: str = payload.get("email")
        provider: str = payload.get("provider")

        if user_id is None or email is None:
            return None

        return TokenData(user_id=user_id, email=email, provider=provider)
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


# HTTP Bearer security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[TokenData]:
    """Get current user from JWT token (optional - returns None if not authenticated).
    Use this for endpoints that work both with and without authentication.
    """
    if credentials is None:
        return None

    token_data = decode_access_token(credentials.credentials)
    return token_data


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> TokenData:
    """Get current user from JWT token (required - raises 401 if not authenticated).
    Use this for protected endpoints that require authentication.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token_data = decode_access_token(credentials.credentials)
    if token_data is None:
        raise credentials_exception

    return token_data


def generate_state_token() -> str:
    """Generate secure state token for OAuth flow."""
    return secrets.token_urlsafe(32)


def verify_state_token(state: str, expected: str) -> bool:
    """Verify OAuth state token to prevent CSRF."""
    return secrets.compare_digest(state, expected)

"""Security utilities for JWT authentication and password hashing."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# Password hashing context - supports PBKDF2 (primary) and bcrypt (legacy)
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30


def get_password_hash(password: str) -> str:
    """Hash a password using PBKDF2 (primary) or bcrypt (fallback)."""
    # Truncate to 72 bytes (bcrypt limit, kept for compatibility)
    password = password[:72]
    try:
        return pwd_context.hash(password)
    except ValueError:
        # Fallback to PBKDF2 if there's an issue
        fallback_ctx = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
        return fallback_ctx.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    plain_password = plain_password[:72]
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except ValueError:
        # Return False if the hash scheme is unsupported
        return False


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token.
    
    Args:
        data: Dictionary containing token claims (e.g., {'sub': 'user_id'})
        expires_delta: Custom expiration time. If None, uses default (30 days)
    
    Returns:
        Encoded JWT token
    
    Raises:
        ValueError: If SECRET_KEY is not configured
    """
    # Validate SECRET_KEY is set
    if not settings.SECRET_KEY:
        raise ValueError("SECRET_KEY environment variable is not set")
    
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    
    to_encode.update({"exp": expire})
    
    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and verify a JWT token.
    
    Args:
        token: JWT token string
    
    Returns:
        Token payload dictionary
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


def get_token_subject(token: str) -> Optional[str]:
    """Extract subject (user_id) from token.
    
    Args:
        token: JWT token string
    
    Returns:
        Subject claim value, or None if invalid
    """
    try:
        payload = decode_token(token)
        return payload.get("sub")
    except HTTPException:
        return None

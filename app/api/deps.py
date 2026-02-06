"""FastAPI dependency injection functions for authentication and database access."""

import logging
from typing import Callable, Generator, Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.crud import crud_user
from app.database import SessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)

# OAuth2 Bearer token scheme
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """
    Dependency to get current authenticated user from JWT token.

    Args:
        token: JWT token from Authorization header
        db: Database session

    Returns:
        User: Authenticated user model

    Raises:
        HTTPException: 401 if token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Debug: Log token prefix for debugging (first 20 chars only for security)
    token_preview = token[:20] + "..." if len(token) > 20 else token
    logger.info(f"[AUTH] Validating token: {token_preview}")

    try:
        payload = decode_token(token)
        phone: str = payload.get("sub")
        logger.info(f"[AUTH] Token decoded successfully. Phone from token: {phone}")
        if phone is None:
            logger.warning("[AUTH] Phone is None in token payload")
            raise credentials_exception
    except HTTPException:
        logger.warning("[AUTH] Token decode failed (HTTPException from decode_token)")
        raise credentials_exception
    except Exception as e:
        logger.warning(f"[AUTH] Token decode failed with exception: {type(e).__name__}: {e}")
        raise credentials_exception

    user = crud_user.get_by_phone(db, phone=phone)
    if user is None:
        logger.warning(f"[AUTH] User not found for phone: {phone}")
        raise credentials_exception

    logger.info(f"[AUTH] User authenticated: id={user.id}, role={user.role}, phone={user.phone}")
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    Dependency to verify current user is active.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User: Active user model
        
    Raises:
        HTTPException: 403 if user is inactive
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Dependency to optionally get current authenticated user.
    Returns None if no valid token provided.

    Useful for endpoints that allow both authenticated and unauthenticated access.

    Args:
        token: Optional JWT token from Authorization header
        db: Database session

    Returns:
        Optional[User]: Authenticated user model or None
    """
    if not token:
        return None

    try:
        payload = decode_token(token)
        phone: str = payload.get("sub")
        if phone is None:
            return None
    except Exception:
        return None

    user = crud_user.get_by_phone(db, phone=phone)
    if user is None or not user.is_active:
        return None

    return user


def require_role(*allowed_roles: str) -> Callable:
    """
    Factory function to create role-based access control dependency.

    Args:
        *allowed_roles: User roles allowed to access the endpoint

    Returns:
        Callable: Dependency function that checks user role

    Raises:
        HTTPException: 403 if user role not in allowed_roles

    Example:
        @router.get("/admin/users")
        async def get_all_users(current_user: User = Depends(require_role("admin"))):
            return {"users": []}
    """
    async def role_checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not enough permissions. Required role(s): {', '.join(allowed_roles)}"
            )
        return current_user

    return role_checker


__all__ = [
    "oauth2_scheme",
    "oauth2_scheme_optional",
    "get_db",
    "get_current_user",
    "get_current_active_user",
    "get_optional_current_user",
    "require_role",
]

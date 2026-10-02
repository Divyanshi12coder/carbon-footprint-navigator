import uuid
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False, description="JWT from /api/auth/login")

DbSession = Annotated[Session, Depends(get_db)]


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def get_current_user(db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _unauthorized("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = uuid.UUID(payload["sub"])
    except jwt.ExpiredSignatureError as exc:
        raise _unauthorized("Session expired. Please sign in again.") from exc
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise _unauthorized("Invalid authentication token") from exc
    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _unauthorized("Account not found or disabled")
    if payload.get("tv") != user.token_version:
        raise _unauthorized("Session has been signed out. Please sign in again.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator access required")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def get_optional_user(db: DbSession, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]) -> User | None:
    """Like get_current_user, but anonymous requests (no Authorization header) are allowed."""
    if credentials is None:
        return None
    return get_current_user(db, credentials)


OptionalUser = Annotated[User | None, Depends(get_optional_user)]

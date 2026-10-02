from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.rate_limit import client_ip, limiter
from app.core.security import create_access_token, hash_password, verify_password
from app.models import User, UserPreference
from app.schemas.auth import ChangePasswordIn, LoginIn, RegisterIn, TokenOut, UserOut
from app.schemas.common import MessageOut

router = APIRouter(prefix="/auth", tags=["auth"])

# Pre-computed hash so failed logins for unknown emails take as long as wrong passwords.
_DUMMY_HASH = hash_password("timing-equaliser-not-a-real-password-1")


def _token_response(user: User) -> TokenOut:
    token, expires_in = create_access_token(str(user.id), user.token_version, user.role)
    return TokenOut(access_token=token, expires_in=expires_in, user=UserOut.model_validate(user))


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, request: Request, db: DbSession) -> TokenOut:
    limiter.check(f"register:{client_ip(request)}", get_settings().rate_limit_auth_per_minute)
    email = payload.email.lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists.")
    user = User(email=email, hashed_password=hash_password(payload.password), full_name=payload.full_name)
    user.preferences = UserPreference()
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, request: Request, db: DbSession) -> TokenOut:
    limiter.check(f"login:{client_ip(request)}", get_settings().rate_limit_auth_per_minute)
    user = db.scalar(select(User).where(func.lower(User.email) == payload.email.lower()))
    if user is None:
        verify_password(payload.password, _DUMMY_HASH)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This account has been disabled.")
    user.last_login_at = datetime.now(UTC)
    db.commit()
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser) -> User:
    return user


@router.post("/logout", response_model=MessageOut)
def logout(user: CurrentUser, db: DbSession) -> MessageOut:
    """Revokes every token issued to this user (token-version bump)."""
    user.token_version += 1
    db.commit()
    return MessageOut(detail="Signed out.")


@router.post("/change-password", response_model=TokenOut)
def change_password(payload: ChangePasswordIn, user: CurrentUser, db: DbSession) -> TokenOut:
    if not verify_password(payload.current_password, user.hashed_password):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect.")
    user.hashed_password = hash_password(payload.new_password)
    user.token_version += 1
    db.commit()
    return _token_response(user)

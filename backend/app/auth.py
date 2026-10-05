import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, Request
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth_models import AdminAccount, CustomerAccount, LoginSession
from app.config import settings
from app.database import get_db
from app.models import Conversation, Customer


COOKIE_NAME = "cx_login_session"
password_hasher = PasswordHash.recommended()
DUMMY_HASH = password_hasher.hash("unknown-account-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    return password_hasher.verify(password, encoded)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def check_origin(request: Request):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    allowed = {origin.strip() for origin in settings.auth_allowed_origins.split(",") if origin.strip()}
    origin = request.headers.get("origin")
    if (origin is not None and origin not in allowed) or request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(status_code=403, detail="Request origin is not allowed")


@dataclass(frozen=True)
class Principal:
    id: UUID
    username: str
    display_name: str
    role: str
    customer_id: UUID | None = None
    brand_id: UUID | None = None


def principal_for(account, db: Session) -> Principal:
    if isinstance(account, AdminAccount):
        return Principal(account.id, account.username, account.display_name, "admin")
    profile = db.get(Customer, account.customer_id)
    if profile is None:
        raise HTTPException(status_code=401, detail="Account profile is unavailable")
    return Principal(account.id, account.username, profile.name, "customer", profile.id, profile.brand_id)


def current_user(request: Request, db: Session = Depends(get_db)) -> Principal:
    check_origin(request)
    token = request.cookies.get(COOKIE_NAME)
    if not token or len(token) > 200:
        raise HTTPException(status_code=401, detail="Please log in")
    session = db.scalar(select(LoginSession).where(
        LoginSession.token_hash == hash_token(token),
        LoginSession.expires_at > datetime.now(timezone.utc),
    ))
    if session is None:
        raise HTTPException(status_code=401, detail="Your session expired. Please log in again.")
    account = db.get(AdminAccount, session.admin_id) if session.admin_id else db.get(CustomerAccount, session.customer_account_id)
    if account is None or not account.is_active:
        raise HTTPException(status_code=401, detail="Account access is unavailable")
    return principal_for(account, db)


def require_admin(user: Principal = Depends(current_user)) -> Principal:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Administrator access is required")
    return user


def conversation_access(request: Request, user: Principal = Depends(current_user), db: Session = Depends(get_db)):
    if user.role == "admin":
        return
    brand_value = request.path_params.get("brand_id")
    conversation_value = request.path_params.get("conversation_id")
    try:
        brand_id = UUID(str(brand_value)) if brand_value else None
        conversation_id = UUID(str(conversation_value)) if conversation_value else None
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid identifier") from None
    if brand_id and brand_id != user.brand_id:
        raise HTTPException(status_code=404, detail="Brand not found")
    if conversation_id:
        owned = db.scalar(select(Conversation.id).where(
            Conversation.id == conversation_id,
            Conversation.brand_id == user.brand_id,
            Conversation.customer_id == user.customer_id,
        ))
        if owned is None:
            raise HTTPException(status_code=404, detail="Conversation not found")

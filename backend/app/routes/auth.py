import secrets
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, ConfigDict, EmailStr, Field, SecretStr, field_validator
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, DUMMY_HASH, Principal, check_origin, current_user, hash_password, hash_token, principal_for, verify_password
from app.auth_models import AdminAccount, CustomerAccount, LoginSession
from app.config import settings
from app.database import get_db
from app.models import Brand, Conversation, Customer


router = APIRouter(prefix="/auth", tags=["Authentication"], dependencies=[Depends(check_origin)])


class UsernameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=60, pattern=r"^[a-zA-Z0-9_.-]+$")

    @field_validator("username", mode="before")
    @classmethod
    def normalize_username(cls, value):
        return value.strip().lower() if isinstance(value, str) else value


class LoginRequest(UsernameRequest):
    role: Literal["admin", "customer"]
    password: SecretStr = Field(min_length=1, max_length=128)


class RegisterRequest(UsernameRequest):
    password: SecretStr = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    brand_id: UUID

    @field_validator("name")
    @classmethod
    def clean_name(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Name cannot be blank")
        return value


class UserResponse(BaseModel):
    id: UUID
    username: str
    display_name: str
    role: Literal["admin", "customer"]
    customer_id: UUID | None = None
    brand_id: UUID | None = None


class RegistrationResponse(BaseModel):
    message: str


class PublicBrand(BaseModel):
    id: UUID
    name: str


def commit(db):
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Account changes could not be saved") from None


@router.get("/brands", response_model=list[PublicBrand])
def registration_brands(db: Session = Depends(get_db)):
    return db.scalars(select(Brand).order_by(Brand.name, Brand.id)).all()


@router.post("/register", status_code=201, response_model=RegistrationResponse)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.get(Brand, body.brand_id) is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    if db.scalar(select(CustomerAccount.id).where(CustomerAccount.username == body.username)):
        raise HTTPException(status_code=409, detail="That customer username is already registered")
    encoded = hash_password(body.password.get_secret_value())
    try:
        # A new account always gets a new profile. Matching an email must never
        # grant access to a pre-existing demo customer's private conversation.
        profile = Customer(brand_id=body.brand_id, name=body.name, email=str(body.email))
        db.add(profile)
        db.flush()
        db.add(CustomerAccount(username=body.username, password_hash=encoded, customer_id=profile.id))
        db.add(Conversation(brand_id=body.brand_id, customer_id=profile.id, status="open"))
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That customer username is already registered") from None
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(status_code=503, detail="Registration could not be saved") from None
    return {"message": "Registration successful. Please log in as a customer."}


@router.post("/login", response_model=UserResponse)
def login(body: LoginRequest, request: Request, response: Response, db: Session = Depends(get_db)):
    model = AdminAccount if body.role == "admin" else CustomerAccount
    account = db.scalar(select(model).where(model.username == body.username).with_for_update())
    valid = verify_password(body.password.get_secret_value(), account.password_hash if account else DUMMY_HASH)
    if account is None or not account.is_active:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    now = datetime.now(timezone.utc)
    if account.locked_until:
        if account.locked_until > now:
            raise HTTPException(status_code=429, detail="Too many attempts. Try again in five minutes.")
        account.failed_attempts = 0
        account.locked_until = None
    if not valid:
        account.failed_attempts += 1
        if account.failed_attempts >= 5:
            account.locked_until = now + timedelta(minutes=5)
        commit(db)
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    account.failed_attempts = 0
    account.locked_until = None
    old_token = request.cookies.get(COOKIE_NAME)
    if old_token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == hash_token(old_token)))
    db.execute(delete(LoginSession).where(LoginSession.expires_at <= now))
    token = secrets.token_urlsafe(32)
    lifetime = timedelta(hours=settings.auth_session_hours)
    db.add(LoginSession(
        admin_id=account.id if body.role == "admin" else None,
        customer_account_id=account.id if body.role == "customer" else None,
        token_hash=hash_token(token), expires_at=now + lifetime,
    ))
    user = asdict(principal_for(account, db))
    commit(db)
    response.set_cookie(COOKIE_NAME, token, max_age=int(lifetime.total_seconds()), path="/", httponly=True, secure=settings.auth_cookie_secure, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return user


@router.get("/me", response_model=UserResponse)
def me(response: Response, user: Principal = Depends(current_user)):
    response.headers["Cache-Control"] = "no-store"
    return asdict(user)


@router.post("/logout", status_code=204)
def logout(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.execute(delete(LoginSession).where(LoginSession.token_hash == hash_token(token)))
        commit(db)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=settings.auth_cookie_secure, samesite="lax")
    response.headers["Cache-Control"] = "no-store"
    return response

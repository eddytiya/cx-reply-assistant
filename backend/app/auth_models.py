"""Separate administrator and customer accounts with revocable sessions."""

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID

from app.database import Base
from app.models import RecordMixin


class CredentialsMixin:
    username = Column(String(120), nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="true")
    failed_attempts = Column(Integer, nullable=False, server_default="0")
    locked_until = Column(DateTime(timezone=True), nullable=True)


class AdminAccount(CredentialsMixin, RecordMixin, Base):
    __tablename__ = "admin_accounts"
    display_name = Column(String(120), nullable=False)
    __table_args__ = (
        CheckConstraint("username = lower(trim(username)) AND length(username) > 0", name="ck_admin_username"),
        CheckConstraint("length(password_hash) > 0", name="ck_admin_password_hash"),
        CheckConstraint("failed_attempts >= 0", name="ck_admin_failed_attempts"),
    )


class CustomerAccount(CredentialsMixin, RecordMixin, Base):
    __tablename__ = "customer_accounts"
    customer_id = Column(UUID(as_uuid=True), ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False, unique=True)
    __table_args__ = (
        CheckConstraint("username = lower(trim(username)) AND length(username) > 0", name="ck_customer_account_username"),
        CheckConstraint("length(password_hash) > 0", name="ck_customer_account_password_hash"),
        CheckConstraint("failed_attempts >= 0", name="ck_customer_account_failed_attempts"),
    )


class LoginSession(RecordMixin, Base):
    __tablename__ = "login_sessions"
    admin_id = Column(UUID(as_uuid=True), ForeignKey("admin_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    customer_account_id = Column(UUID(as_uuid=True), ForeignKey("customer_accounts.id", ondelete="CASCADE"), nullable=True, index=True)
    token_hash = Column(String(64), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    __table_args__ = (
        CheckConstraint("(admin_id IS NOT NULL) <> (customer_account_id IS NOT NULL)", name="ck_login_session_one_account"),
    )

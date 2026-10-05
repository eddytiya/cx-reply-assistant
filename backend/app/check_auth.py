"""Exercise real authentication routes; roll back all temporary test records."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.auth import COOKIE_NAME, hash_password, hash_token, verify_password
from app.auth_models import AdminAccount, CustomerAccount, LoginSession
from app.config import settings
from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models import Brand, Conversation, Customer, Message, Order, KnowledgeEntry, ReplyGeneration
from app.seed import seed_id


MODELS = (AdminAccount, CustomerAccount, LoginSession, Customer, Conversation, Message, Order, KnowledgeEntry, ReplyGeneration)


def database_counts():
    with SessionLocal() as db:
        return {model.__tablename__: db.scalar(select(func.count()).select_from(model)) for model in MODELS}


def check_auth():
    before = database_counts()
    suffix = uuid4().hex[:10]
    admin_name = f"auth-check-{suffix}"
    password = "Temporary-test-password-42"
    nike = str(seed_id("nike/brand"))
    adidas = str(seed_id("adidas/brand"))
    old_conversation = str(seed_id("nike/conversation"))
    connection = engine.connect()
    outer = connection.begin()

    def test_db():
        with Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False, expire_on_commit=False) as db:
            yield db

    app.dependency_overrides[get_db] = test_db

    def register(client, username):
        return client.post("/auth/register", json={
            "username": username, "name": "Temporary Auth Customer",
            "email": "aarav@example.com", "password": password, "brand_id": nike,
        })

    try:
        with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
            assert db.get(Brand, seed_id("nike/brand")) is not None
            real_admin = db.scalar(select(AdminAccount).where(AdminAccount.username == settings.admin_username.strip().lower()))
            assert real_admin is not None
            assert verify_password(settings.admin_password.get_secret_value(), real_admin.password_hash)
            assert real_admin.password_hash.startswith("$argon2id$")
            db.add(AdminAccount(username=admin_name, display_name="Temporary Test Admin", password_hash=hash_password(password)))
            db.commit()

        with TestClient(app) as anonymous, TestClient(app) as customer, TestClient(app) as second, TestClient(app) as admin:
            assert anonymous.get("/brands").status_code == 401
            assert anonymous.get("/auth/me").status_code == 401
            assert len(anonymous.get("/auth/brands").json()) >= 2
            print("PASS: anonymous users see login/registration data, not private conversations")

            for payload in (
                {"username": "invalid space", "name": "Test", "email": "test@example.com", "password": password, "brand_id": nike},
                {"username": "valid-name", "name": "   ", "email": "test@example.com", "password": password, "brand_id": nike},
                {"username": "valid-name", "name": "Test", "email": "test@example.com", "password": "short", "brand_id": nike},
                {"username": "valid-name", "name": "Test", "email": "test@example.com", "password": password, "brand_id": nike, "role": "admin"},
            ):
                assert anonymous.post("/auth/register", json=payload).status_code == 422
            assert anonymous.post("/auth/register", json={"username": "valid-name", "name": "Test", "email": "test@example.com", "password": password, "brand_id": str(uuid4())}).status_code == 404
            print("PASS: registration validates inputs and cannot create an admin")

            name = f"customer-{suffix}"
            assert register(customer, name).status_code == 201
            assert register(customer, name.upper()).status_code == 409
            assert customer.get("/brands").status_code == 401
            assert customer.post("/auth/login", json={"username": name, "password": "wrong-password", "role": "customer"}).status_code == 401
            response = customer.post("/auth/login", json={"username": name.upper(), "password": password, "role": "customer"})
            assert response.status_code == 200, response.text
            assert "httponly" in response.headers["set-cookie"].lower()
            assert "samesite=lax" in response.headers["set-cookie"].lower()
            assert "password" not in response.json()
            assert customer.get("/auth/me").json()["role"] == "customer"
            profile_id = response.json()["customer_id"]
            assert profile_id != str(seed_id("nike/customer"))
            with Session(bind=connection) as db:
                account = db.scalar(select(CustomerAccount).where(CustomerAccount.username == name))
                assert account.password_hash.startswith("$argon2id$")
                assert verify_password(password, account.password_hash)
                assert not verify_password("wrong", account.password_hash)
                token = customer.cookies.get(COOKIE_NAME)
                assert db.scalar(select(LoginSession.id).where(LoginSession.token_hash == hash_token(token)))
                assert not db.scalar(select(LoginSession.id).where(LoginSession.token_hash == token))
            print("PASS: customer registration/login, normalized usernames, password hashing and hashed sessions")

            assert [b["id"] for b in customer.get("/brands").json()] == [nike]
            owned = customer.get(f"/brands/{nike}/conversations").json()
            assert len(owned) == 1
            cid = owned[0]["id"]
            base = f"/brands/{nike}/conversations/{cid}"
            assert customer.get(base).status_code == 200
            assert customer.get(f"/brands/{adidas}/conversations").status_code == 404
            assert customer.get(f"/brands/{nike}/conversations/{old_conversation}").status_code == 404
            assert customer.post(base + "/messages", json={"sender_role": "agent", "content": "Forbidden"}).status_code == 403
            assert customer.post(base + "/messages", json={"sender_role": "customer", "content": "Temporary customer message"}).status_code == 201
            print("PASS: customer sees only their own brand/conversation and cannot impersonate an agent")

            for method, path in (
                ("GET", f"/brands/{nike}/knowledge"),
                ("POST", f"/brands/{nike}/knowledge"),
                ("PUT", f"/brands/{nike}/knowledge/{uuid4()}"),
                ("DELETE", f"/brands/{nike}/knowledge/{uuid4()}"),
                ("GET", base + "/reply-generations"),
                ("POST", base + "/reply-generations"),
                ("PUT", base + f"/reply-generations/{uuid4()}/edit"),
                ("POST", base + f"/reply-generations/{uuid4()}/approve"),
            ):
                assert customer.request(method, path).status_code == 403
            assert customer.post(base + "/messages", headers={"Origin": "https://untrusted.example"}, json={"sender_role": "customer", "content": "Forbidden"}).status_code == 403
            assert anonymous.post("/auth/login", headers={"Origin": "https://untrusted.example"}, json={"username": name, "password": password, "role": "customer"}).status_code == 403
            print("PASS: customer blocked from all policy/AI operations; untrusted browser writes blocked")

            other_name = f"other-{suffix}"
            assert register(second, other_name).status_code == 201
            assert second.post("/auth/login", json={"username": other_name, "password": password, "role": "customer"}).status_code == 200
            assert second.get(base).status_code == 404
            print("PASS: another customer of the SAME brand cannot access this conversation")

            assert admin.post("/auth/login", json={"username": admin_name, "password": password, "role": "admin"}).status_code == 200
            assert admin.get("/auth/me").json()["role"] == "admin"
            assert len(admin.get("/brands").json()) >= 2
            for brand in (nike, adidas):
                assert admin.get(f"/brands/{brand}/knowledge").status_code == 200
                assert admin.get(f"/brands/{brand}/conversations").status_code == 200
            assert admin.get(base).status_code == 200
            reply = admin.post(base + "/messages", json={"sender_role": "agent", "content": "Temporary support reply"})
            assert reply.status_code == 201
            assert any(message["id"] == reply.json()["id"] and message["sender_role"] == "agent" for message in customer.get(base).json()["messages"])
            print("PASS: admin accesses both brands and customer/admin messages share one conversation")

            for _ in range(5):
                assert second.post("/auth/login", json={"username": other_name, "password": "wrong", "role": "customer"}).status_code == 401
            assert second.post("/auth/login", json={"username": other_name, "password": password, "role": "customer"}).status_code == 429
            print("PASS: repeated wrong passwords trigger temporary account lockout")

            with patch.object(Session, "commit", side_effect=SQLAlchemyError("Simulated failure")):
                failed = register(anonymous, f"rollback-{suffix}")
                assert failed.status_code == 503
            with Session(bind=connection) as db:
                assert db.scalar(select(CustomerAccount.id).where(CustomerAccount.username == f"rollback-{suffix}")) is None
            print("PASS: failed registration rolls back account/profile/conversation changes")

            old_token = customer.cookies.get(COOKIE_NAME)
            assert customer.post("/auth/logout").status_code == 204
            assert customer.get("/brands").status_code == 401
            customer.cookies.set(COOKIE_NAME, old_token)
            assert customer.get("/auth/me").status_code == 401
            print("PASS: logout revokes the session; replaying its old cookie fails")

            admin_token = admin.cookies.get(COOKIE_NAME)
            with Session(bind=connection, join_transaction_mode="create_savepoint") as db:
                session = db.scalar(select(LoginSession).where(LoginSession.token_hash == hash_token(admin_token)))
                session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
                db.commit()
            assert admin.get("/auth/me").status_code == 401
            print("PASS: expired sessions are rejected")
    finally:
        app.dependency_overrides.pop(get_db, None)
        outer.rollback()
        connection.close()

    assert database_counts() == before, "Temporary test data was not completely rolled back"
    print("PASS: temporary test records rolled back; existing data preserved; no Gemini calls")


if __name__ == "__main__":
    check_auth()

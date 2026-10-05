from sqlalchemy import select

from app.auth import hash_password
from app.auth_models import AdminAccount
from app.config import settings
from app.database import SessionLocal


def seed_admin():
    username = settings.admin_username.strip().lower()
    password = settings.admin_password.get_secret_value()
    if not username or not password:
        raise ValueError("Admin credentials cannot be blank")
    if settings.auth_cookie_secure and password == "admin":
        raise ValueError("Change the demo ADMIN_PASSWORD before public deployment")
    with SessionLocal.begin() as db:
        if db.scalar(select(AdminAccount.id).where(AdminAccount.username == username)):
            print("Admin already exists; its password was preserved.")
            return
        db.add(AdminAccount(username=username, display_name="Support Administrator", password_hash=hash_password(password)))
    print("Demo administrator created. Only the password hash was stored.")


if __name__ == "__main__":
    seed_admin()

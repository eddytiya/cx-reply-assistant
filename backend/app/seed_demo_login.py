"""Create a reviewer login for the fictional seeded Meera profile."""
from sqlalchemy import select

from app.auth import hash_password
from app.auth_models import CustomerAccount
from app.database import SessionLocal
from app.models import Customer
from app.seed import seed_id

DEMO_USERNAME = "meera.demo"
DEMO_PASSWORD = "MeeraDemo2026!"


def seed_demo_login():
    profile_id = seed_id("adidas/customer")
    with SessionLocal.begin() as db:
        profile = db.get(Customer, profile_id)
        if profile is None:
            raise RuntimeError("Run the original demo seed before creating Meera's login")
        existing = db.scalar(select(CustomerAccount).where(CustomerAccount.customer_id == profile_id))
        if existing is not None:
            print("Meera's customer account already exists; credentials preserved.")
            return
        taken = db.scalar(select(CustomerAccount.id).where(CustomerAccount.username == DEMO_USERNAME))
        if taken is not None:
            raise RuntimeError("Demo username is already assigned to another profile")
        db.add(CustomerAccount(username=DEMO_USERNAME, password_hash=hash_password(DEMO_PASSWORD), customer_id=profile_id))
    print("Meera demo customer login created for the existing fictional Adidas profile.")


if __name__ == "__main__":
    seed_demo_login()

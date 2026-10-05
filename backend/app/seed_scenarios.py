"""Add repeatable demo conversations without replacing existing project data."""

from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import Brand, Conversation, Customer, Message, Order
from app.seed import seed_id


SCENARIOS = [
    ("damaged", "Damaged item", "delivered", 2, [
        "My bottle was delivered two days ago, but it is broken. What can I do?",
    ]),
    ("refund", "Refund within window", "delivered", 5, [
        "I received this bottle 5 days ago. What are the conditions for a refund?",
    ]),
    ("return-10-days", "Return after 10 days", "delivered", 10, [
        "I received this unopened bottle 10 days ago. Can I return it?",
    ]),
    ("expired-refund", "Refund after 20 days", "delivered", 20, [
        "I received this bottle 20 days ago. Can I get a refund?",
    ]),
    ("shipping", "Shipping and tracking", "shipped", None, [
        "My order has shipped. How long does standard shipping take, and when is tracking available?",
    ]),
    ("cancellation", "Cancellation before dispatch", "placed", None, [
        "I placed my order one hour ago and it has not been dispatched. Can I cancel it?",
    ]),
    ("follow-up", "Damaged item follow-up", "delivered", 2, [
        "My bottle arrived broken two days ago. What can I do?",
        "I have the photos ready. How should I share them?",
    ]),
    ("unsupported", "No relevant policy", "delivered", 2, [
        "Can you help me plan a cryptocurrency investment portfolio?",
    ]),
    ("no-order", "Missing order information", None, None, [
        "My bottle is damaged and I want a refund, but I cannot find my order details.",
    ]),
]


def scenario_id(brand_key, scenario_key, record):
    return seed_id(f"scenarios/v1/{brand_key}/{scenario_key}/{record}")


def seed_scenarios():
    now = datetime.now(timezone.utc)
    counts = dict(customers=0, orders=0, conversations=0, messages=0)

    with SessionLocal.begin() as db:
        for brand_key in ("nike", "adidas"):
            brand = db.get(Brand, seed_id(f"{brand_key}/brand"))
            if brand is None:
                raise RuntimeError("Run python -m app.seed first to create the demo brands.")

            for index, (key, label, status, days, messages) in enumerate(SCENARIOS, 1):
                conversation_id = scenario_id(brand_key, key, "conversation")
                if db.get(Conversation, conversation_id) is not None:
                    continue

                # Distinct dates make demo list ordering predictable. Dates and
                # messages are kept unchanged when this script is run again.
                requested_at = now - timedelta(minutes=index)
                customer_id = scenario_id(brand_key, key, "customer")
                db.add(Customer(
                    id=customer_id,
                    brand_id=brand.id,
                    name=f"Demo {index:02d}: {label}",
                    email=f"{brand_key}.{key}@example.com",
                    created_at=requested_at - timedelta(days=30),
                ))
                db.flush()
                counts["customers"] += 1

                order_id = None
                if status is not None:
                    order_id = scenario_id(brand_key, key, "order")
                    delivered_at = (
                        requested_at - timedelta(days=days)
                        if days is not None else None
                    )
                    placed_at = (
                        requested_at - timedelta(hours=1)
                        if status == "placed" else
                        (delivered_at or requested_at) - timedelta(days=6)
                    )
                    db.add(Order(
                        id=order_id,
                        brand_id=brand.id,
                        customer_id=customer_id,
                        order_number=f"{brand_key.upper()}-TEST-{index:02d}",
                        item_name=f"{brand.name} Demo Water Bottle",
                        status=status,
                        delivered_at=delivered_at,
                        created_at=placed_at,
                    ))
                    db.flush()
                    counts["orders"] += 1

                db.add(Conversation(
                    id=conversation_id,
                    brand_id=brand.id,
                    customer_id=customer_id,
                    order_id=order_id,
                    status="open",
                    created_at=requested_at,
                ))
                db.flush()
                counts["conversations"] += 1

                for message_index, content in enumerate(messages):
                    db.add(Message(
                        id=scenario_id(brand_key, key, f"message-{message_index}"),
                        brand_id=brand.id,
                        conversation_id=conversation_id,
                        sender_role="customer",
                        content=content,
                        created_at=requested_at + timedelta(seconds=message_index),
                    ))
                    counts["messages"] += 1
                db.flush()

    print("Fictional demo scenarios seeded successfully.")
    for table, count in counts.items():
        print(f"New {table}: {count}")
    print("Existing records and policies were preserved. No AI replies were prefilled.")
    for brand_key in ("nike", "adidas"):
        for index, (key, label, *_rest) in enumerate(SCENARIOS, 1):
            print(f"{brand_key.title()} | Demo {index:02d}: {label} | "
                  f"{scenario_id(brand_key, key, 'conversation')}")


if __name__ == "__main__":
    seed_scenarios()

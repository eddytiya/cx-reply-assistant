from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from app.database import SessionLocal
from app.models import (
    Brand,
    Conversation,
    Customer,
    KnowledgeEntry,
    Message,
    Order,
)


def seed_id(key: str):
    """Generate the same UUID for the same demo record key."""
    return uuid5(
        NAMESPACE_URL,
        f"cx-reply-assistant/demo/{key}",
    )


def insert_if_missing(db, model, key: str, **values):
    """Insert a demo record only if its fixed ID is missing."""
    record_id = seed_id(key)
    existing = db.get(model, record_id)

    if existing is not None:
        return False

    db.add(model(id=record_id, **values))

    # Insert into the current transaction before creating
    # records that reference this record.
    db.flush()

    return True


DEMO_BRANDS = [
    {
        "key": "nike",
        "name": "Nike",
        "customer_name": "Aarav Sharma",
        "customer_email": "aarav@example.com",
        "order_number": "NIKE-DEMO-1001",
        "item_name": "Nike Demo Water Bottle",
        "days_since_delivery": 2,
        "message": (
            "My order was delivered two days ago, "
            "but the bottle is broken. What can I do?"
        ),
        "policies": [
            {
                "category": "return",
                "title": "Demo: Returns and damaged items",
                "content": (
                    "Fictional assessment policy, not Nike's actual policy. "
                    "Unopened items may be returned if the customer "
                    "contacts support within 7 days of delivery. "
                    "For an item that arrived broken or damaged, "
                    "contact support within 7 days of delivery and "
                    "provide the order number and clear photos of "
                    "the damage and packaging. Support reviews the "
                    "evidence before confirming a replacement or refund."
                ),
            },
            {
                "category": "refund",
                "title": "Demo: Refund eligibility and processing",
                "content": (
                    "Fictional assessment policy, not Nike's actual policy. "
                    "Refund requests must be reported within 7 days "
                    "of delivery. Damaged-item refunds require review "
                    "of photos showing the damage and packaging. "
                    "Once approved, refunds are processed to the "
                    "original payment method within 5 business days. "
                    "Requests outside the 7-day window require "
                    "manual review; a refund is not guaranteed."
                ),
            },
            {
                "category": "shipping",
                "title": "Demo: Shipping and delivery",
                "content": (
                    "Fictional assessment policy, not Nike's actual policy. "
                    "Standard delivery takes 3 to 5 business days "
                    "after dispatch. Tracking is available once the "
                    "order ships. This is an estimated delivery window, "
                    "not a guaranteed arrival date."
                ),
            },
            {
                "category": "cancellation",
                "title": "Demo: Order cancellation",
                "content": (
                    "Fictional assessment policy, not Nike's actual policy. "
                    "Orders may be cancelled before dispatch. "
                    "Once dispatched, an order cannot be cancelled "
                    "and the return policy applies after delivery."
                ),
            },
        ],
    },
    {
        "key": "adidas",
        "name": "Adidas",
        "customer_name": "Meera Patel",
        "customer_email": "meera@example.com",
        "order_number": "ADIDAS-DEMO-2001",
        "item_name": "Adidas Demo Water Bottle",
        "days_since_delivery": 20,
        "message": (
            "I received this bottle 20 days ago. "
            "Can I return it and get a refund?"
        ),
        "policies": [
            {
                "category": "return",
                "title": "Demo: Returns and damaged items",
                "content": (
                    "Fictional assessment policy, not Adidas's actual policy. "
                    "Unused items in their original packaging may "
                    "be returned if the customer contacts support "
                    "within 14 days of delivery. Items that arrived "
                    "broken or damaged must also be reported within "
                    "14 days. Provide the order number and photos "
                    "of the item and packaging for support review "
                    "before a resolution is confirmed."
                ),
            },
            {
                "category": "refund",
                "title": "Demo: Refund eligibility and processing",
                "content": (
                    "Fictional assessment policy, not Adidas's actual policy. "
                    "Refund requests must be reported within 14 days "
                    "of delivery. For an approved standard return, "
                    "a refund is issued after the returned item "
                    "passes inspection. Approved refunds are "
                    "processed to the original payment method "
                    "within 7 business days. Requests outside the "
                    "14-day window require manual review; "
                    "a refund is not guaranteed."
                ),
            },
            {
                "category": "shipping",
                "title": "Demo: Shipping and delivery",
                "content": (
                    "Fictional assessment policy, not Adidas's actual policy. "
                    "Standard delivery takes 5 to 7 business days "
                    "after dispatch. Tracking is available once the "
                    "order ships. This is an estimated delivery window, "
                    "not a guaranteed arrival date."
                ),
            },
            {
                "category": "cancellation",
                "title": "Demo: Order cancellation",
                "content": (
                    "Fictional assessment policy, not Adidas's actual policy. "
                    "Orders may be cancelled within 2 hours of "
                    "placement, provided they have not been dispatched. "
                    "After that window or after dispatch, cancellation "
                    "is unavailable and the return policy applies."
                ),
            },
        ],
    },
]


def seed_database():
    now = datetime.now(timezone.utc)

    counts = {
        "brands": 0,
        "customers": 0,
        "orders": 0,
        "conversations": 0,
        "messages": 0,
        "knowledge_entries": 0,
    }

    # All inserts commit together. If an insert fails,
    # the transaction rolls back.
    with SessionLocal.begin() as db:
        for demo in DEMO_BRANDS:
            key = demo["key"]

            brand_key = f"{key}/brand"
            customer_key = f"{key}/customer"
            order_key = f"{key}/order"
            conversation_key = f"{key}/conversation"
            message_key = f"{key}/initial-message"

            brand_id = seed_id(brand_key)
            customer_id = seed_id(customer_key)
            order_id = seed_id(order_key)
            conversation_id = seed_id(conversation_key)

            counts["brands"] += insert_if_missing(
                db,
                Brand,
                brand_key,
                name=demo["name"],
            )

            for policy in demo["policies"]:
                counts["knowledge_entries"] += insert_if_missing(
                    db,
                    KnowledgeEntry,
                    f"{key}/policy/{policy['category']}",
                    brand_id=brand_id,
                    category=policy["category"],
                    title=policy["title"],
                    content=policy["content"],
                )

            counts["customers"] += insert_if_missing(
                db,
                Customer,
                customer_key,
                brand_id=brand_id,
                name=demo["customer_name"],
                email=demo["customer_email"],
            )

            delivered_at = now - timedelta(
                days=demo["days_since_delivery"]
            )

            counts["orders"] += insert_if_missing(
                db,
                Order,
                order_key,
                brand_id=brand_id,
                customer_id=customer_id,
                order_number=demo["order_number"],
                item_name=demo["item_name"],
                status="delivered",
                delivered_at=delivered_at,
                created_at=delivered_at - timedelta(days=6),
            )

            counts["conversations"] += insert_if_missing(
                db,
                Conversation,
                conversation_key,
                brand_id=brand_id,
                customer_id=customer_id,
                order_id=order_id,
                status="open",
            )

            # Do not add another initial message if the
            # conversation already contains any messages.
            existing_message = db.scalar(
                select(Message.id)
                .where(
                    Message.brand_id == brand_id,
                    Message.conversation_id == conversation_id,
                )
                .limit(1)
            )

            if existing_message is None:
                counts["messages"] += insert_if_missing(
                    db,
                    Message,
                    message_key,
                    brand_id=brand_id,
                    conversation_id=conversation_id,
                    sender_role="customer",
                    content=demo["message"],
                )

    print("Seeding completed successfully.")
    print(
        "Demo only: brand names are real; policies, "
        "products, customers, and orders are fictional."
    )
    print("New records inserted:")

    for table, count in counts.items():
        print(f"  {table}: {count}")


if __name__ == "__main__":
    seed_database()
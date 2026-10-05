import re
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brand, KnowledgeEntry


# A damaged-item question can require both return and refund policies.
CATEGORY_PATTERNS = {
    "return": [
        r"\breturns?\b",
        r"\breturning\b",
        r"\breplacements?\b",
        r"\bexchanges?\b",
        r"\bbroken\b",
        r"\bdamaged?\b",
        r"\bdefective\b",
        r"\bleaking\b",
        r"\bshattered\b",
    ],
    "refund": [
        r"\brefunds?\b",
        r"\breimburse(?:ment)?\b",
        r"\bmoney back\b",
        r"\bbroken\b",
        r"\bdamaged?\b",
        r"\bdefective\b",
        r"\bleaking\b",
        r"\bshattered\b",
    ],
    "shipping": [
        r"\bshipping\b",
        r"\btracking\b",
        r"\bdispatch(?:ed)?\b",
        r"\bdelivery\b",
        r"\bdelayed?\b",
        r"\blate\b",
        r"\bwhere is my order\b",
        r"\bwhen will\b",
        r"\bnot arrived\b",
        r"\bnot delivered\b",
    ],
    "cancellation": [
        r"\bcancel(?:led|ed|ling|ing|lation|lations)?\b",
        r"\bstop my order\b",
    ],
}


# These phrases may depend on an earlier customer request.
FOLLOW_UP_PATTERNS = [
    r"\bphotos?\b",
    r"\bpictures?\b",
    r"\bimages?\b",
    r"\bwhat next\b",
    r"\bnext steps?\b",
    r"\bhow should i\b",
    r"\bhow do i proceed\b",
    r"\bwhat should i do\b",
    r"\bplease proceed\b",
]


def identify_categories(message: str) -> list[str]:
    """Identify policy categories mentioned in a message."""
    return [
        category
        for category, patterns in CATEGORY_PATTERNS.items()
        if any(
            re.search(pattern, message, flags=re.IGNORECASE)
            for pattern in patterns
        )
    ]


def is_follow_up(message: str) -> bool:
    return any(
        re.search(pattern, message, flags=re.IGNORECASE)
        for pattern in FOLLOW_UP_PATTERNS
    )


def retrieve_policies(
    db: Session,
    brand_id: UUID,
    customer_message: str,
    recent_customer_messages: list[str] | None = None,
) -> dict:
    """
    Retrieve current policies for the selected brand.

    recent_customer_messages must:
    - belong to the same conversation;
    - exclude customer_message;
    - be ordered oldest to newest.
    """
    if db.get(Brand, brand_id) is None:
        raise ValueError("Brand not found")

    if not customer_message.strip():
        raise ValueError("Customer message cannot be blank")

    matched_categories = identify_categories(customer_message)
    retrieval_message = customer_message
    used_previous_message = False

    # Only borrow earlier context for a recognizable follow-up.
    # An unrelated new question should not inherit old policies.
    if not matched_categories and is_follow_up(customer_message):
        previous_messages = recent_customer_messages or []

        for previous_message in reversed(previous_messages[-5:]):
            previous_categories = identify_categories(previous_message)

            if previous_categories:
                matched_categories = previous_categories
                retrieval_message = previous_message
                used_previous_message = True
                break

    if not matched_categories:
        return {
            "status": "needs_review",
            "reason": "No relevant policy category was identified.",
            "brand_id": str(brand_id),
            "customer_message": customer_message,
            "retrieval_message": retrieval_message,
            "used_previous_message": used_previous_message,
            "matched_categories": [],
            "missing_categories": [],
            "entries": [],
        }

    statement = (
        select(KnowledgeEntry)
        .where(
            KnowledgeEntry.brand_id == brand_id,
            KnowledgeEntry.category.in_(matched_categories),
        )
        .order_by(
            KnowledgeEntry.category,
            KnowledgeEntry.created_at,
            KnowledgeEntry.id,
        )
    )

    entries = db.scalars(statement).all()

    available_categories = {entry.category for entry in entries}
    missing_categories = [
        category
        for category in matched_categories
        if category not in available_categories
    ]

    if not entries:
        result_status = "needs_review"
        reason = "No policies exist for the identified categories."

    elif missing_categories:
        result_status = "needs_review"
        reason = "Some relevant policy categories are missing."

    else:
        result_status = "context_found"
        reason = "Policies were found for the identified categories."

    return {
        "status": result_status,
        "reason": reason,
        "brand_id": str(brand_id),
        "customer_message": customer_message,
        "retrieval_message": retrieval_message,
        "used_previous_message": used_previous_message,
        "matched_categories": matched_categories,
        "missing_categories": missing_categories,
        "entries": [
            {
                "id": str(entry.id),
                "brand_id": str(entry.brand_id),
                "category": entry.category,
                "title": entry.title,
                "content": entry.content,
                "updated_at": entry.updated_at.isoformat(),
            }
            for entry in entries
        ],
    }
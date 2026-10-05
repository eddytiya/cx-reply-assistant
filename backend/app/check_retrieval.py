from uuid import UUID

from app.database import SessionLocal
from app.services.retrieval import retrieve_policies


NIKE_ID = UUID("60fc920d-a80e-5c64-9a1a-18e4444f2738")
ADIDAS_ID = UUID("076fabac-ae0b-549d-af01-b30909cb0c56")


def print_result(label: str, result: dict):
    print(f"\n--- {label} ---")
    print("Status:", result["status"])
    print("Reason:", result["reason"])
    print("Categories:", result["matched_categories"])
    print("Missing categories:", result["missing_categories"])
    print("Used earlier message:", result["used_previous_message"])

    for entry in result["entries"]:
        print(
            "Policy:",
            entry["category"],
            "|",
            entry["title"],
            "| Brand:",
            entry["brand_id"],
        )


def check_retrieval():
    with SessionLocal() as db:
        nike_result = retrieve_policies(
            db=db,
            brand_id=NIKE_ID,
            customer_message="My bottle arrived broken.",
        )

        assert nike_result["status"] == "context_found"
        assert set(nike_result["matched_categories"]) == {
            "return",
            "refund",
        }
        assert all(
            entry["brand_id"] == str(NIKE_ID)
            for entry in nike_result["entries"]
        )

        print_result("Nike damaged item", nike_result)

        adidas_result = retrieve_policies(
            db=db,
            brand_id=ADIDAS_ID,
            customer_message=(
                "I received this 20 days ago. Can I get a refund?"
            ),
        )

        assert adidas_result["status"] == "context_found"
        assert adidas_result["matched_categories"] == ["refund"]
        assert all(
            entry["brand_id"] == str(ADIDAS_ID)
            for entry in adidas_result["entries"]
        )

        print_result("Adidas refund request", adidas_result)

        follow_up_result = retrieve_policies(
            db=db,
            brand_id=NIKE_ID,
            customer_message=(
                "I have the photos ready. How should I share them?"
            ),
            recent_customer_messages=[
                "My bottle arrived broken.",
            ],
        )

        assert follow_up_result["used_previous_message"] is True
        assert set(follow_up_result["matched_categories"]) == {
            "return",
            "refund",
        }

        print_result("Follow-up message", follow_up_result)

        unknown_result = retrieve_policies(
            db=db,
            brand_id=NIKE_ID,
            customer_message="Do you offer engraving?",
            recent_customer_messages=[
                "My bottle arrived broken.",
            ],
        )

        assert unknown_result["status"] == "needs_review"
        assert unknown_result["entries"] == []
        assert unknown_result["used_previous_message"] is False

        print_result("Unsupported question", unknown_result)

    print("\nAll retrieval checks passed.")


if __name__ == "__main__":
    check_retrieval()
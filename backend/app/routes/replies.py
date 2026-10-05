from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import (
    Brand,
    Conversation,
    Customer,
    Message,
    Order,
    ReplyGeneration,
)
from app.schemas import (
    DraftEditRequest,
    MessageResponse,
    OrderResponse,
    ReplyGenerationResponse,
)
from app.services.ai_reply import generate_draft
from app.services.retrieval import retrieve_policies


router = APIRouter(
    prefix="/brands/{brand_id}/conversations/{conversation_id}/reply-generations",
    tags=["AI Reply Generation"],
)


def get_conversation_or_404(
    db: Session,
    brand_id: UUID,
    conversation_id: UUID,
):
    conversation = db.scalar(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.brand_id == brand_id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation not found",
        )

    return conversation


@router.get("", response_model=list[ReplyGenerationResponse])
def list_reply_generations(
    brand_id: UUID,
    conversation_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    get_conversation_or_404(db, brand_id, conversation_id)

    return db.scalars(
        select(ReplyGeneration)
        .where(
            ReplyGeneration.brand_id == brand_id,
            ReplyGeneration.conversation_id == conversation_id,
        )
        .order_by(
            ReplyGeneration.created_at.desc(),
            ReplyGeneration.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    ).all()


@router.post(
    "",
    response_model=ReplyGenerationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reply_generation(
    brand_id: UUID,
    conversation_id: UUID,
    db: Session = Depends(get_db),
):
    conversation = get_conversation_or_404(
        db,
        brand_id,
        conversation_id,
    )

    if conversation.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Cannot generate a reply for a closed conversation",
        )

    brand = db.get(Brand, brand_id)

    customer = db.scalar(
        select(Customer).where(
            Customer.id == conversation.customer_id,
            Customer.brand_id == brand_id,
        )
    )

    if brand is None or customer is None:
        raise HTTPException(
            status_code=404,
            detail="Conversation context not found",
        )

    # Read the latest six customer messages for retrieval context.
    customer_messages = list(
        db.scalars(
            select(Message)
            .where(
                Message.brand_id == brand_id,
                Message.conversation_id == conversation_id,
                Message.sender_role == "customer",
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(6)
        ).all()
    )

    customer_messages.reverse()

    if not customer_messages:
        raise HTTPException(
            status_code=409,
            detail="A customer message is required before generation",
        )

    latest_customer = customer_messages[-1]

    retrieval = retrieve_policies(
        db=db,
        brand_id=brand_id,
        customer_message=latest_customer.content,
        recent_customer_messages=[
            message.content for message in customer_messages[:-1]
        ],
    )

    # For follow-ups, assess delivery age at the relevant earlier request.
    relevant_request = latest_customer

    if retrieval["used_previous_message"]:
        relevant_request = next(
            message
            for message in reversed(customer_messages[:-1])
            if message.content == retrieval["retrieval_message"]
        )

    history = list(
        db.scalars(
            select(Message)
            .where(
                Message.brand_id == brand_id,
                Message.conversation_id == conversation_id,
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(20)
        ).all()
    )

    history.reverse()

    order = None

    if conversation.order_id is not None:
        order = db.scalar(
            select(Order).where(
                Order.id == conversation.order_id,
                Order.brand_id == brand_id,
                Order.customer_id == conversation.customer_id,
            )
        )

        if order is None:
            raise HTTPException(
                status_code=404,
                detail="Order context not found",
            )

    order_context = None

    if order is not None:
        order_context = OrderResponse.model_validate(
            order
        ).model_dump(mode="json")

        elapsed = None

        if order.delivered_at is not None:
            elapsed = (
                relevant_request.created_at - order.delivered_at
            ).total_seconds() / 86400

        order_context["days_since_delivery_at_request"] = elapsed

    context_snapshot = {
        "brand": {
            "id": str(brand.id),
            "name": brand.name,
        },
        "customer": {
            "id": str(customer.id),
            "name": customer.name,
        },
        "conversation_id": str(conversation_id),
        "customer_message_id": str(latest_customer.id),
        "customer_message": latest_customer.content,
        "order": order_context,
        "messages": [
            MessageResponse.model_validate(message).model_dump(mode="json")
            for message in history
        ],
        "retrieval": retrieval,
    }

    # Copy values before ending the read transaction.
    customer_message_id = latest_customer.id
    customer_message_text = latest_customer.content

    # Release the read transaction before waiting on Gemini.
    # No changes have been made in this transaction.
    db.rollback()

    result = generate_draft(context_snapshot)

    # Store evaluation details alongside the exact supplied context.
    context_snapshot["generation_result"] = {
        "review_reason": result["review_reason"],
        "used_policy_ids": result["used_policy_ids"],
        "model_called": result["model_called"],
    }

    record = ReplyGeneration(
        brand_id=brand_id,
        conversation_id=conversation_id,
        customer_message_id=customer_message_id,
        customer_message_snapshot=customer_message_text,
        context_snapshot=context_snapshot,
        ai_response=result["draft"],
        status=result["status"],
        model_name=settings.gemini_model,
        error_code=result["error_code"],
    )

    try:
        db.add(record)
        db.flush()
        db.refresh(record)

        response = ReplyGenerationResponse.model_validate(record)

        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Generation log could not be saved",
        ) from None

    if result["status"] == "failed":
        raise HTTPException(
            status_code=502,
            detail={
                "message": result["review_reason"],
                "generation_id": str(response.id),
                "error_code": result["error_code"],
            },
        )

    return response

def get_generation_for_update(
    db: Session,
    brand_id: UUID,
    conversation_id: UUID,
    generation_id: UUID,
):
    record = db.scalar(
        select(ReplyGeneration)
        .where(
            ReplyGeneration.id == generation_id,
            ReplyGeneration.brand_id == brand_id,
            ReplyGeneration.conversation_id == conversation_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Reply generation not found",
        )

    return record

@router.put(
    "/{generation_id}/edit",
    response_model=ReplyGenerationResponse,
)
def edit_reply_draft(
    brand_id: UUID,
    conversation_id: UUID,
    generation_id: UUID,
    payload: DraftEditRequest,
    db: Session = Depends(get_db),
):
    try:
        conversation = get_conversation_or_404(
            db,
            brand_id,
            conversation_id,
        )

        if conversation.status != "open":
            raise HTTPException(
                status_code=409,
                detail="Cannot edit a draft for a closed conversation",
            )

        record = get_generation_for_update(
            db,
            brand_id,
            conversation_id,
            generation_id,
        )

        if record.status == "sent":
            raise HTTPException(
                status_code=409,
                detail="A sent reply cannot be edited",
            )

        if record.status == "failed":
            raise HTTPException(
                status_code=409,
                detail="Generation failed. Regenerate or send a manual message.",
            )

        record.agent_edited_response = payload.content

        db.flush()
        db.refresh(record)

        response = ReplyGenerationResponse.model_validate(record)

        db.commit()

        return response

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Draft edit could not be saved",
        ) from None

@router.post(
    "/{generation_id}/approve",
    response_model=ReplyGenerationResponse,
)
def approve_reply_draft(
    brand_id: UUID,
    conversation_id: UUID,
    generation_id: UUID,
    db: Session = Depends(get_db),
):
    try:
        record = get_generation_for_update(
            db,
            brand_id,
            conversation_id,
            generation_id,
        )

        # Repeated approval returns the original result.
        # It does not create another message.
        if record.status == "sent":
            return ReplyGenerationResponse.model_validate(record)

        conversation = get_conversation_or_404(
            db,
            brand_id,
            conversation_id,
        )

        if conversation.status != "open":
            raise HTTPException(
                status_code=409,
                detail="Cannot send a reply to a closed conversation",
            )

        if record.status == "failed":
            raise HTTPException(
                status_code=409,
                detail="Generation failed. Regenerate or send a manual message.",
            )

        latest_customer_message = db.scalar(
            select(Message)
            .where(
                Message.brand_id == brand_id,
                Message.conversation_id == conversation_id,
                Message.sender_role == "customer",
            )
            .order_by(Message.created_at.desc(), Message.id.desc())
            .limit(1)
        )

        if (
            latest_customer_message is None
            or latest_customer_message.id != record.customer_message_id
        ):
            raise HTTPException(
                status_code=409,
                detail=(
                    "A newer customer message exists. "
                    "Generate a new draft before approval."
                ),
            )

        final_text = (
            record.agent_edited_response
            if record.agent_edited_response is not None
            else record.ai_response
        )

        if final_text is None or not final_text.strip():
            raise HTTPException(
                status_code=409,
                detail="A non-empty reply is required before approval",
            )

        final_text = final_text.strip()

        message = Message(
            brand_id=brand_id,
            conversation_id=conversation_id,
            sender_role="agent",
            content=final_text,
        )

        db.add(message)
        db.flush()

        record.final_response = final_text
        record.final_message_id = message.id
        record.status = "sent"

        db.flush()
        db.refresh(record)

        response = ReplyGenerationResponse.model_validate(record)

        # Save the message and its generation-log update together.
        db.commit()

        return response

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Approved reply could not be saved",
        ) from None
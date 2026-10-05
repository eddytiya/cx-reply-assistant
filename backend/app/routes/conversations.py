from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import Principal, current_user
from app.models import Brand, Conversation, Customer, Message, Order
from app.schemas import (
    BrandResponse,
    ConversationDetailResponse,
    ConversationResponse,
    CustomerResponse,
    MessageCreate,
    MessageResponse,
    OrderResponse,
)


router = APIRouter(
    prefix="/brands",
    tags=["Brands and Conversations"],
)


def get_brand_or_404(db: Session, brand_id: UUID):
    brand = db.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=404,
            detail="Brand not found",
        )

    return brand


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


@router.get("", response_model=list[BrandResponse])
def list_brands(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: Principal = Depends(current_user),
):
    statement = (
        select(Brand)
        .order_by(Brand.name, Brand.id)
        .limit(limit)
        .offset(offset)
    )

    if user.role == "customer":
        statement = statement.where(Brand.id == user.brand_id)
    return db.scalars(statement).all()


@router.get(
    "/{brand_id}/conversations",
    response_model=list[ConversationResponse],
)
def list_conversations(
    brand_id: UUID,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: Principal = Depends(current_user),
):
    get_brand_or_404(db, brand_id)

    statement = (
        select(Conversation)
        .where(Conversation.brand_id == brand_id)
        .order_by(
            Conversation.created_at.desc(),
            Conversation.id.desc(),
        )
        .limit(limit)
        .offset(offset)
    )

    if user.role == "customer":
        statement = statement.where(Conversation.customer_id == user.customer_id)
    return db.scalars(statement).all()


@router.get(
    "/{brand_id}/conversations/{conversation_id}",
    response_model=ConversationDetailResponse,
)
def get_conversation_detail(
    brand_id: UUID,
    conversation_id: UUID,
    db: Session = Depends(get_db),
):
    brand = get_brand_or_404(db, brand_id)

    conversation = get_conversation_or_404(
        db,
        brand_id,
        conversation_id,
    )

    customer = db.scalar(
        select(Customer).where(
            Customer.id == conversation.customer_id,
            Customer.brand_id == brand_id,
        )
    )

    if customer is None:
        raise HTTPException(
            status_code=404,
            detail="Customer not found",
        )

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
                detail="Order not found",
            )

    messages = db.scalars(
        select(Message)
        .where(
            Message.brand_id == brand_id,
            Message.conversation_id == conversation_id,
        )
        .order_by(Message.created_at, Message.id)
    ).all()

    latest_customer_message = next(
        (
            message
            for message in reversed(messages)
            if message.sender_role == "customer"
        ),
        None,
    )

    return ConversationDetailResponse(
        conversation=ConversationResponse.model_validate(conversation),
        brand=BrandResponse.model_validate(brand),
        customer=CustomerResponse.model_validate(customer),
        order=(
            OrderResponse.model_validate(order)
            if order is not None
            else None
        ),
        messages=[
            MessageResponse.model_validate(message)
            for message in messages
        ],
        latest_customer_message=(
            MessageResponse.model_validate(latest_customer_message)
            if latest_customer_message is not None
            else None
        ),
    )


@router.post(
    "/{brand_id}/conversations/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_message(
    brand_id: UUID,
    conversation_id: UUID,
    payload: MessageCreate,
    db: Session = Depends(get_db),
    user: Principal = Depends(current_user),
):
    if user.role == "customer" and payload.sender_role != "customer":
        raise HTTPException(status_code=403, detail="Customers can only send customer messages")
    get_brand_or_404(db, brand_id)

    conversation = get_conversation_or_404(
        db,
        brand_id,
        conversation_id,
    )

    if conversation.status != "open":
        raise HTTPException(
            status_code=409,
            detail="Cannot send messages to a closed conversation",
        )

    message = Message(
        brand_id=conversation.brand_id,
        conversation_id=conversation.id,
        sender_role=payload.sender_role,
        content=payload.content,
    )

    try:
        db.add(message)

        # Execute the insert and load database-generated values.
        db.flush()
        db.refresh(message)

        response = MessageResponse.model_validate(message)

        # Make the message permanent only after validation succeeds.
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Message could not be saved",
        ) from None

    return response

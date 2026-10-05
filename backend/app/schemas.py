from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ORMResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class BrandResponse(ORMResponse):
    id: UUID
    name: str
    created_at: datetime


class CustomerResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    name: str
    email: str | None
    created_at: datetime


class OrderResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    customer_id: UUID
    order_number: str
    item_name: str
    status: str
    delivered_at: datetime | None
    created_at: datetime


class ConversationResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    customer_id: UUID
    order_id: UUID | None
    status: str
    created_at: datetime


class MessageResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    conversation_id: UUID
    sender_role: Literal["customer", "agent"]
    content: str
    created_at: datetime


class ConversationDetailResponse(BaseModel):
    conversation: ConversationResponse
    brand: BrandResponse
    customer: CustomerResponse
    order: OrderResponse | None
    messages: list[MessageResponse]
    latest_customer_message: MessageResponse | None


class MessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_role: Literal["customer", "agent"]
    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Message content cannot be blank")

        return cleaned

PolicyCategory = Literal[
    "return",
    "refund",
    "shipping",
    "cancellation",
]


class KnowledgeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: PolicyCategory
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)

    @field_validator("title", "content")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Title and content cannot be blank")

        return cleaned


class KnowledgeUpdate(KnowledgeCreate):
    pass


class KnowledgeResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    category: PolicyCategory
    title: str
    content: str
    created_at: datetime
    updated_at: datetime

class ReplyGenerationResponse(ORMResponse):
    id: UUID
    brand_id: UUID
    conversation_id: UUID
    customer_message_id: UUID
    customer_message_snapshot: str
    context_snapshot: dict
    ai_response: str | None
    agent_edited_response: str | None
    final_response: str | None
    final_message_id: UUID | None
    status: Literal["generated", "needs_review", "sent", "failed"]
    model_name: str
    error_code: str | None
    created_at: datetime
    updated_at: datetime

class DraftEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1, max_length=5000)

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        cleaned = value.strip()

        if not cleaned:
            raise ValueError("Edited reply cannot be blank")

        return cleaned
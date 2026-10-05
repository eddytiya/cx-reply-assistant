from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.database import Base


# Shared columns inherited by all seven models.
class RecordMixin:
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Brand(RecordMixin, Base):
    __tablename__ = "brands"

    name = Column(String(120), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_brands_name_not_blank",
        ),
    )


class Customer(RecordMixin, Base):
    __tablename__ = "customers"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name = Column(String(120), nullable=False)
    email = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "brand_id",
            "id",
            name="uq_customers_brand_id",
        ),
        CheckConstraint(
            "length(trim(name)) > 0",
            name="ck_customers_name_not_blank",
        ),
    )


class Order(RecordMixin, Base):
    __tablename__ = "orders"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    order_number = Column(String(80), nullable=False)
    item_name = Column(String(200), nullable=False)
    status = Column(
        String(20),
        nullable=False,
        server_default="placed",
    )
    delivered_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        ForeignKeyConstraint(
            ["brand_id", "customer_id"],
            ["customers.brand_id", "customers.id"],
            name="fk_orders_brand_customer",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "brand_id",
            "order_number",
            name="uq_orders_brand_number",
        ),
        UniqueConstraint(
            "brand_id",
            "customer_id",
            "id",
            name="uq_orders_brand_customer_id",
        ),
        CheckConstraint(
            "status IN ('placed', 'shipped', 'delivered', 'cancelled')",
            name="ck_orders_status",
        ),
        CheckConstraint(
            "length(trim(order_number)) > 0",
            name="ck_orders_number_not_blank",
        ),
        CheckConstraint(
            "length(trim(item_name)) > 0",
            name="ck_orders_item_not_blank",
        ),
        Index("ix_orders_brand_customer", "brand_id", "customer_id"),
    )


class Conversation(RecordMixin, Base):
    __tablename__ = "conversations"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    customer_id = Column(UUID(as_uuid=True), nullable=False)
    order_id = Column(UUID(as_uuid=True), nullable=True)
    status = Column(
        String(20),
        nullable=False,
        server_default="open",
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["brand_id", "customer_id"],
            ["customers.brand_id", "customers.id"],
            name="fk_conversations_brand_customer",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["brand_id", "customer_id", "order_id"],
            ["orders.brand_id", "orders.customer_id", "orders.id"],
            name="fk_conversations_customer_order",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "brand_id",
            "id",
            name="uq_conversations_brand_id",
        ),
        CheckConstraint(
            "status IN ('open', 'closed')",
            name="ck_conversations_status",
        ),
        Index(
            "ix_conversations_brand_customer",
            "brand_id",
            "customer_id",
        ),
        Index(
            "ix_conversations_customer_order",
            "brand_id",
            "customer_id",
            "order_id",
        ),
    )


class Message(RecordMixin, Base):
    __tablename__ = "messages"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    sender_role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)

    __table_args__ = (
        ForeignKeyConstraint(
            ["brand_id", "conversation_id"],
            ["conversations.brand_id", "conversations.id"],
            name="fk_messages_brand_conversation",
            ondelete="RESTRICT",
        ),
        UniqueConstraint(
            "brand_id",
            "conversation_id",
            "id",
            name="uq_messages_brand_conversation_id",
        ),
        CheckConstraint(
            "sender_role IN ('customer', 'agent')",
            name="ck_messages_sender_role",
        ),
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_messages_content_not_blank",
        ),
        Index(
            "ix_messages_conversation_created",
            "brand_id",
            "conversation_id",
            "created_at",
        ),
    )


class KnowledgeEntry(RecordMixin, Base):
    __tablename__ = "knowledge_entries"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    category = Column(String(30), nullable=False)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "category IN ('return', 'refund', 'shipping', 'cancellation')",
            name="ck_knowledge_entries_category",
        ),
        CheckConstraint(
            "length(trim(title)) > 0",
            name="ck_knowledge_entries_title_not_blank",
        ),
        CheckConstraint(
            "length(trim(content)) > 0",
            name="ck_knowledge_entries_content_not_blank",
        ),
        Index(
            "ix_knowledge_entries_brand_category",
            "brand_id",
            "category",
        ),
    )


class ReplyGeneration(RecordMixin, Base):
    __tablename__ = "reply_generations"

    brand_id = Column(
        UUID(as_uuid=True),
        ForeignKey("brands.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    conversation_id = Column(UUID(as_uuid=True), nullable=False)
    customer_message_id = Column(UUID(as_uuid=True), nullable=False)

    customer_message_snapshot = Column(Text, nullable=False)
    context_snapshot = Column(JSONB, nullable=False)

    ai_response = Column(Text, nullable=True)
    agent_edited_response = Column(Text, nullable=True)
    final_response = Column(Text, nullable=True)

    final_message_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        unique=True,
    )
    status = Column(
        String(20),
        nullable=False,
        server_default="generated",
    )
    model_name = Column(String(120), nullable=False)
    error_code = Column(String(80), nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        ForeignKeyConstraint(
            ["brand_id", "conversation_id"],
            ["conversations.brand_id", "conversations.id"],
            name="fk_reply_generations_brand_conversation",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["brand_id", "conversation_id", "customer_message_id"],
            ["messages.brand_id", "messages.conversation_id", "messages.id"],
            name="fk_reply_generations_customer_message",
            ondelete="RESTRICT",
        ),
        ForeignKeyConstraint(
            ["brand_id", "conversation_id", "final_message_id"],
            ["messages.brand_id", "messages.conversation_id", "messages.id"],
            name="fk_reply_generations_final_message",
            ondelete="RESTRICT",
        ),
        CheckConstraint(
            "status IN ('generated', 'needs_review', 'sent', 'failed')",
            name="ck_reply_generations_status",
        ),
        CheckConstraint(
            "length(trim(customer_message_snapshot)) > 0",
            name="ck_reply_generations_customer_snapshot_not_blank",
        ),
        CheckConstraint(
            "length(trim(model_name)) > 0",
            name="ck_reply_generations_model_not_blank",
        ),
        CheckConstraint(
            "status != 'sent' OR "
            "(final_message_id IS NOT NULL AND final_response IS NOT NULL)",
            name="ck_reply_generations_sent_has_message",
        ),
        Index(
            "ix_reply_generations_conversation_created",
            "brand_id",
            "conversation_id",
            "created_at",
        ),
        Index(
            "ix_reply_generations_customer_message",
            "brand_id",
            "conversation_id",
            "customer_message_id",
        ),
        Index(
            "ix_reply_generations_final_message",
            "brand_id",
            "conversation_id",
            "final_message_id",
        ),
    )
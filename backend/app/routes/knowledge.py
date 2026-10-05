from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Brand, KnowledgeEntry
from app.schemas import (
    KnowledgeCreate,
    KnowledgeResponse,
    KnowledgeUpdate,
    PolicyCategory,
)


router = APIRouter(
    prefix="/brands/{brand_id}/knowledge",
    tags=["Knowledge Base"],
)


def get_brand_or_404(db: Session, brand_id: UUID):
    brand = db.get(Brand, brand_id)

    if brand is None:
        raise HTTPException(
            status_code=404,
            detail="Brand not found",
        )

    return brand


def get_entry_or_404(
    db: Session,
    brand_id: UUID,
    entry_id: UUID,
):
    entry = db.scalar(
        select(KnowledgeEntry).where(
            KnowledgeEntry.id == entry_id,
            KnowledgeEntry.brand_id == brand_id,
        )
    )

    if entry is None:
        raise HTTPException(
            status_code=404,
            detail="Knowledge entry not found",
        )

    return entry


@router.get("", response_model=list[KnowledgeResponse])
def list_knowledge(
    brand_id: UUID,
    category: PolicyCategory | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    get_brand_or_404(db, brand_id)

    statement = select(KnowledgeEntry).where(
        KnowledgeEntry.brand_id == brand_id
    )

    if category is not None:
        statement = statement.where(
            KnowledgeEntry.category == category
        )

    statement = (
        statement
        .order_by(
            KnowledgeEntry.category,
            KnowledgeEntry.created_at,
            KnowledgeEntry.id,
        )
        .limit(limit)
        .offset(offset)
    )

    return db.scalars(statement).all()


@router.post(
    "",
    response_model=KnowledgeResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_knowledge(
    brand_id: UUID,
    payload: KnowledgeCreate,
    db: Session = Depends(get_db),
):
    get_brand_or_404(db, brand_id)

    entry = KnowledgeEntry(
        brand_id=brand_id,
        category=payload.category,
        title=payload.title,
        content=payload.content,
    )

    try:
        db.add(entry)
        db.flush()
        db.refresh(entry)

        response = KnowledgeResponse.model_validate(entry)

        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Knowledge entry could not be saved",
        ) from None

    return response


@router.put(
    "/{entry_id}",
    response_model=KnowledgeResponse,
)
def update_knowledge(
    brand_id: UUID,
    entry_id: UUID,
    payload: KnowledgeUpdate,
    db: Session = Depends(get_db),
):
    get_brand_or_404(db, brand_id)
    entry = get_entry_or_404(db, brand_id, entry_id)

    try:
        entry.category = payload.category
        entry.title = payload.title
        entry.content = payload.content

        db.flush()
        db.refresh(entry)

        response = KnowledgeResponse.model_validate(entry)

        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Knowledge entry could not be updated",
        ) from None

    return response


@router.delete(
    "/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_knowledge(
    brand_id: UUID,
    entry_id: UUID,
    db: Session = Depends(get_db),
):
    get_brand_or_404(db, brand_id)
    entry = get_entry_or_404(db, brand_id, entry_id)

    try:
        db.delete(entry)
        db.commit()

    except SQLAlchemyError:
        db.rollback()

        raise HTTPException(
            status_code=503,
            detail="Knowledge entry could not be deleted",
        ) from None

    return Response(status_code=status.HTTP_204_NO_CONTENT)
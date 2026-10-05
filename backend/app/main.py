from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import conversation_access, require_admin
from app.routes.auth import router as auth_router
from app.routes.conversations import router as conversations_router
from app.routes.knowledge import router as knowledge_router
from app.routes.replies import router as replies_router

app = FastAPI(
    title="CX Reply Assistant API",
    description="Backend for an AI-assisted customer support application.",
    version="0.1.0",
)

app.include_router(auth_router)
app.include_router(conversations_router, dependencies=[Depends(conversation_access)])
app.include_router(knowledge_router, dependencies=[Depends(require_admin)])
app.include_router(replies_router, dependencies=[Depends(require_admin)])


@app.get("/")
def read_root():
    return {
        "message": "CX Reply Assistant API is running",
        "docs": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "ok",
    }


@app.get("/health/db")
def database_health_check(db: Session = Depends(get_db)):
    try:
        result = db.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise HTTPException(
            status_code=503,
            detail="Database is unavailable",
        ) from None

    if result != 1:
        raise HTTPException(
            status_code=503,
            detail="Database check failed",
        )

    return {
        "status": "ok",
        "database": "connected",
    }

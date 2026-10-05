"""Serve the built React app and API under a single public origin."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.main import app as api_app

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api_app)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parent.parent / "static", html=True), name="frontend")

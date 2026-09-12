from fastapi import FastAPI
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug
)


@app.get("/")
def home():
    return {
        "message": "Welcome to Enterprise RAG Chatbot"
    }


@app.get("/about")
def about():
    return {
        "project": settings.app_name,
        "version": settings.app_version
    }


@app.get("/health")
def health():
    return {
        "status": "Healthy"
    }


@app.get("/developer")
def developer():
    return {
        "name": "Shiva",
        "role": "AI Engineer",
        "project": settings.app_name
    }


@app.get("/health/database")
def database_health():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        value = result.scalar()

    return {
        "database": "PostgreSQL",
        "status": "Connected",
        "test_result": value
    }
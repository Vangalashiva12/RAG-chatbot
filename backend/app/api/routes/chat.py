from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.document import Document
from app.models.user import User
from app.services.rag_service import generate_rag_answer
from app.core.permissions import get_current_user


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=10)


class ChatSource(BaseModel):
    document_id: int
    filename: str
    chunk_index: int


class ChatResponse(BaseModel):
    question: str
    answer: str
    sources: list[ChatSource]


@router.post("/", response_model=ChatResponse)
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    answer, chunks = generate_rag_answer(
        question=request.question,
        db=db,
        top_k=request.top_k
    )

    document_ids = list(
        {chunk.document_id for chunk in chunks}
    )

    documents = (
        db.query(Document)
        .filter(Document.id.in_(document_ids))
        .all()
    )

    document_map = {
        document.id: document
        for document in documents
    }

    sources = []

    for chunk in chunks:
        document = document_map.get(chunk.document_id)

        if document:
            sources.append(
                ChatSource(
                    document_id=document.id,
                    filename=document.filename,
                    chunk_index=chunk.chunk_index
                )
            )

    return ChatResponse(
        question=request.question,
        answer=answer,
        sources=sources
    )
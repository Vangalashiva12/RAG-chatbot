from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.permissions import get_current_user
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.rag_service import generate_rag_answer


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


# ============================================================
# Request Schema
# ============================================================

class ChatRequest(BaseModel):
    question: str
    conversation_id: int
    top_k: int = 5


# ============================================================
# Citation Schema
# ============================================================

class SourceResponse(BaseModel):
    document_id: int
    filename: str
    chunk_id: int
    chunk_index: int
    similarity_score: float


# ============================================================
# Chat Response Schema
# ============================================================

class ChatResponse(BaseModel):
    conversation_id: int
    question: str
    answer: str
    sources: list[SourceResponse]


# ============================================================
# Chat Endpoint
# ============================================================

@router.post(
    "/",
    response_model=ChatResponse
)
def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    # ---------------------------------------------------------
    # 1. Find the conversation
    # ---------------------------------------------------------

    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == request.conversation_id,
            Conversation.user_id == current_user.id
        )
        .first()
    )

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found"
        )

    # ---------------------------------------------------------
    # 2. Save user's message
    # ---------------------------------------------------------

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question
    )

    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # ---------------------------------------------------------
    # 3. Run RAG pipeline
    # ---------------------------------------------------------

    try:

        answer, chunks = generate_rag_answer(
            question=request.question,
            db=db,
            conversation_id=conversation.id,
            top_k=request.top_k
        )

    except Exception as error:

        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate RAG response: {str(error)}"
        )

    # ---------------------------------------------------------
    # 4. Save assistant's response
    # ---------------------------------------------------------

    assistant_message = Message(
        conversation_id=conversation.id,
        role="assistant",
        content=answer
    )

    db.add(assistant_message)

    # ---------------------------------------------------------
    # 5. Update conversation timestamp
    # ---------------------------------------------------------

    conversation.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(assistant_message)

    # ---------------------------------------------------------
    # 6. Prepare citation sources
    # ---------------------------------------------------------

    sources = []

    for chunk, document, similarity_score in chunks:

        sources.append(
            SourceResponse(
                document_id=document.id,
                filename=document.filename,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                similarity_score=round(
                    similarity_score,
                    4
                )
            )
        )

    # ---------------------------------------------------------
    # 7. Return response
    # ---------------------------------------------------------

    return ChatResponse(
        conversation_id=conversation.id,
        question=request.question,
        answer=answer,
        sources=sources
    )
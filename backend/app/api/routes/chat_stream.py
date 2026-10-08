import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.permissions import get_current_user
from app.core.database import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.services.llm_service import bedrock_service
from app.services.rag_service import (
    build_context,
    build_conversation_history,
    get_conversation_history,
    retrieve_hybrid_context,
)


router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


class ChatStreamRequest(BaseModel):
    question: str
    conversation_id: int
    top_k: int = 5


def format_sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


@router.post("/stream")
def chat_stream(
    request: ChatStreamRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
            status_code=404,
            detail="Conversation not found"
        )

    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        content=request.question
    )

    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    chunks = retrieve_hybrid_context(
        question=request.question,
        db=db,
        top_k=request.top_k
    )

    if not chunks:

        answer = (
            "I couldn't find relevant information "
            "in the provided documents."
        )

        assistant_message = Message(
            conversation_id=conversation.id,
            role="assistant",
            content=answer
        )

        db.add(assistant_message)

        conversation.updated_at = datetime.now(timezone.utc)

        db.commit()

        def empty_stream():
            yield format_sse(
                {
                    "type": "token",
                    "content": answer
                }
            )

            yield format_sse(
                {
                    "type": "sources",
                    "sources": []
                }
            )

            yield format_sse(
                {
                    "type": "done"
                }
            )

        return StreamingResponse(
            empty_stream(),
            media_type="text/event-stream"
        )

    context = build_context(chunks)

    messages = get_conversation_history(
        conversation_id=conversation.id,
        db=db
    )

    conversation_history = build_conversation_history(
        messages
    )

    def generate():
        full_answer = ""

        try:
            for token in bedrock_service.generate_answer_stream(
                question=request.question,
                context=context,
                conversation_history=conversation_history
            ):
                full_answer += token

                yield format_sse(
                    {
                        "type": "token",
                        "content": token
                    }
                )

            assistant_message = Message(
                conversation_id=conversation.id,
                role="assistant",
                content=full_answer
            )

            db.add(assistant_message)

            conversation.updated_at = datetime.now(
                timezone.utc
            )

            db.commit()

            sources = []

            for chunk, document, rerank_score in chunks:
                sources.append(
                    {
                        "document_id": document.id,
                        "filename": document.filename,
                        "chunk_id": chunk.id,
                        "chunk_index": chunk.chunk_index,
                        "rerank_score": round(
                            float(rerank_score),
                            4
                        )
                    }
                )

            yield format_sse(
                {
                    "type": "sources",
                    "sources": sources
                }
            )

            yield format_sse(
                {
                    "type": "done"
                }
            )

        except Exception as error:
            db.rollback()

            yield format_sse(
                {
                    "type": "error",
                    "message": str(error)
                }
            )

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
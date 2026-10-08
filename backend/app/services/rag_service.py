from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.services.embedding_service import embedding_service
from app.services.llm_service import bedrock_service
from app.services.reranker_service import reranker_service
from app.services.hybrid_search_service import hybrid_search_service


def retrieve_vector_context(
    question: str,
    db: Session,
    top_k: int = 20
) -> list[tuple[DocumentChunk, Document, float]]:

    question_embedding = embedding_service.generate_embedding(
        question
    )

    distance = DocumentChunk.embedding.cosine_distance(
        question_embedding
    )

    results = (
        db.query(
            DocumentChunk,
            Document,
            distance.label("distance")
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id
        )
        .filter(
            DocumentChunk.embedding.is_not(None)
        )
        .order_by(distance)
        .limit(top_k)
        .all()
    )

    if not results:
        return []

    return [
        (
            chunk,
            document,
            1 - float(distance)
        )
        for chunk, document, distance in results
    ]


def rerank_chunks(
    question: str,
    chunks: list[tuple[DocumentChunk, Document, float]],
    top_k: int = 5
) -> list[tuple[DocumentChunk, Document, float]]:

    return reranker_service.rerank(
        question=question,
        chunks=chunks,
        top_k=top_k
    )


def retrieve_hybrid_context(
    question: str,
    db: Session,
    top_k: int = 5
) -> list[tuple[DocumentChunk, Document, float]]:

    hybrid_candidates = hybrid_search_service.search(
        question=question,
        db=db,
        top_k=max(top_k * 4, 20)
    )

    return rerank_chunks(
        question=question,
        chunks=hybrid_candidates,
        top_k=top_k
    )


def build_context(chunks):
    context_parts = []

    for index, (chunk, document, score) in enumerate(
        chunks,
        start=1
    ):
        context_parts.append(
            f"Retrieved Context {index}:\n"
            f"{chunk.content}"
        )

    return "\n\n".join(context_parts)


def get_conversation_history(
    conversation_id,
    db,
    limit=10
):
    messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id
        )
        .order_by(
            Message.created_at.desc()
        )
        .limit(limit)
        .all()
    )

    messages.reverse()

    return messages


def build_conversation_history(messages):
    if not messages:
        return "No previous conversation history."

    history_parts = []

    for message in messages:
        role = message.role.capitalize()

        history_parts.append(
            f"{role}: {message.content}"
        )

    return "\n".join(history_parts)


def generate_rag_answer(
    question: str,
    db: Session,
    conversation_id: int,
    top_k: int = 5
):
    chunks = retrieve_hybrid_context(
        question=question,
        db=db,
        top_k=top_k
    )

    if not chunks:
        return (
            "I couldn't find relevant information in the provided documents.",
            []
        )

    context = build_context(chunks)

    messages = get_conversation_history(
        conversation_id=conversation_id,
        db=db
    )

    conversation_history = build_conversation_history(
        messages
    )

    answer = bedrock_service.generate_answer(
        question=question,
        context=context,
        conversation_history=conversation_history
    )

    return answer, chunks
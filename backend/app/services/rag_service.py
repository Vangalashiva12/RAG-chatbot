from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.services.embedding_service import embedding_service
from app.services.llm_service import bedrock_service
from app.services.reranker_service import reranker_service


def retrieve_context(
    question: str,
    db: Session,
    top_k: int = 5
) -> list[tuple[DocumentChunk, Document, float]]:

    # Generate question embedding
    question_embedding = embedding_service.generate_embedding(
        question
    )

    # Retrieve more candidates than we ultimately need
    candidate_k = max(top_k * 4, 20)

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
        .limit(candidate_k)
        .all()
    )

    if not results:
        return []

    candidate_chunks = []

    for chunk, document, cosine_distance in results:

        vector_similarity = (
            1 - float(cosine_distance)
        )

        candidate_chunks.append(
            (
                chunk,
                document,
                vector_similarity
            )
        )

    # Rerank the vector-search candidates
    reranked_chunks = reranker_service.rerank(
        question=question,
        chunks=candidate_chunks,
        top_k=top_k
    )

    return reranked_chunks

def build_context(
    chunks: list[tuple[DocumentChunk, Document, float]]
) -> str:

    context_parts = []

    for index, (
        chunk,
        document,
        similarity_score
    ) in enumerate(chunks, start=1):

        context_parts.append(
            f"Retrieved Context {index}:\n"
            f"{chunk.content}"
        )

    return "\n\n".join(context_parts)


def get_conversation_history(
    conversation_id: int,
    db: Session,
    limit: int = 10
) -> list[Message]:

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


def build_conversation_history(
    messages: list[Message]
) -> str:

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
) -> tuple[
    str,
    list[tuple[DocumentChunk, Document, float]]
]:

    # ---------------------------------------------------------
    # Retrieve + rerank relevant chunks
    # ---------------------------------------------------------

    chunks = retrieve_context(
        question=question,
        db=db,
        top_k=top_k
    )

    if not chunks:

        return (
            "I couldn't find relevant information "
            "in the provided documents.",
            []
        )

    # ---------------------------------------------------------
    # Build document context
    # ---------------------------------------------------------

    context = build_context(
        chunks
    )

    # ---------------------------------------------------------
    # Get conversation history
    # ---------------------------------------------------------

    messages = get_conversation_history(
        conversation_id=conversation_id,
        db=db
    )

    conversation_history = build_conversation_history(
        messages
    )

    # ---------------------------------------------------------
    # Generate answer
    # ---------------------------------------------------------

    answer = bedrock_service.generate_answer(
        question=question,
        context=context,
        conversation_history=conversation_history
    )

    return answer, chunks
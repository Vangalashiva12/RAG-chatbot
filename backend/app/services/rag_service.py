from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.message import Message
from app.services.embedding_service import embedding_service
from app.services.llm_service import bedrock_service


def retrieve_context(
    question: str,
    db: Session,
    top_k: int = 5
) -> list[tuple[DocumentChunk, Document, float]]:
    """
    Retrieve the most relevant document chunks using semantic
    similarity search.

    The document metadata is retrieved in the same database
    query to avoid N+1 database queries.

    Returns:
        List of:
        (DocumentChunk, Document, similarity_score)
    """

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
        .order_by(
            distance
        )
        .limit(top_k)
        .all()
    )

    retrieved_chunks = []

    for chunk, document, cosine_distance in results:

        similarity_score = 1 - float(cosine_distance)

        retrieved_chunks.append(
            (
                chunk,
                document,
                similarity_score
            )
        )

    return retrieved_chunks


def build_context(
    chunks: list[tuple[DocumentChunk, Document, float]]
) -> str:
    """
    Convert retrieved document chunks into a single context
    string for the LLM.
    """

    context_parts = []

    for index, (chunk, document, similarity_score) in enumerate(
        chunks,
        start=1
    ):
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
    """
    Retrieve recent messages from a conversation.
    """

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
    """
    Convert conversation messages into text that can be
    provided to the LLM.
    """

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
) -> tuple[str, list[tuple[DocumentChunk, Document, float]]]:
    """
    Complete conversational RAG pipeline:

    1. Retrieve conversation history
    2. Retrieve relevant document chunks
    3. Build document context
    4. Build conversation history
    5. Generate an answer using Bedrock
    """

    chunks = retrieve_context(
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
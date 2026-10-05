from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.llm_service import bedrock_service


def retrieve_context(
    question: str,
    db: Session,
    top_k: int = 5
) -> list[DocumentChunk]:
    """
    Retrieve the most relevant document chunks for a user question
    using semantic similarity search.
    """

    question_embedding = embedding_service.generate_embedding(question)

    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.embedding.is_not(None))
        .order_by(
            DocumentChunk.embedding.cosine_distance(question_embedding)
        )
        .limit(top_k)
        .all()
    )

    return chunks


def build_context(chunks: list[DocumentChunk]) -> str:
    """
    Convert retrieved document chunks into a single context string
    for the LLM.
    """

    context_parts = []

    for index, chunk in enumerate(chunks, start=1):
        context_parts.append(
            f"Retrieved Context {index}:\n"
            f"{chunk.content}"
        )

    return "\n\n".join(context_parts)


def generate_rag_answer(
    question: str,
    db: Session,
    top_k: int = 5
) -> tuple[str, list[DocumentChunk]]:
    """
    Complete RAG pipeline:
    1. Retrieve relevant chunks
    2. Build context
    3. Generate an answer using Gemini
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

    answer = bedrock_service.generate_answer(
        question=question,
        context=context
    )

    return answer, chunks
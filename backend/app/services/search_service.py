from sqlalchemy.orm import Session

from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embedding_service


def semantic_search(
    query: str,
    db: Session,
    top_k: int = 5
):
    query_embedding = embedding_service.generate_embedding(query)

    results = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.embedding.is_not(None))
        .order_by(
            DocumentChunk.embedding.cosine_distance(
                query_embedding
            )
        )
        .limit(top_k)
        .all()
    )

    return results
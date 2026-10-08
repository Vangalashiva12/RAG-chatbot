from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk


class KeywordSearchService:

    def search(
        self,
        question: str,
        db: Session,
        top_k: int = 20
    ) -> list[tuple[DocumentChunk, Document, float]]:

        if not question.strip():
            return []

        search_query = func.plainto_tsquery(
            "english",
            question
        )

        search_vector = func.to_tsvector(
            "english",
            DocumentChunk.content
        )

        rank = func.ts_rank_cd(
            search_vector,
            search_query
        )

        results = (
            db.query(
                DocumentChunk,
                Document,
                rank.label("keyword_score")
            )
            .join(
                Document,
                Document.id == DocumentChunk.document_id
            )
            .filter(
                search_vector.op("@@")(search_query)
            )
            .order_by(
                rank.desc()
            )
            .limit(top_k)
            .all()
        )

        return [
            (
                chunk,
                document,
                float(keyword_score)
            )
            for chunk, document, keyword_score in results
        ]


keyword_search_service = KeywordSearchService()
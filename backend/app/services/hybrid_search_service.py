from collections import defaultdict

from sqlalchemy.orm import Session

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.embedding_service import embedding_service
from app.services.keyword_search_service import keyword_search_service


RRF_K = 60


class HybridSearchService:

    def vector_search(
        self,
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

        return [
            (
                chunk,
                document,
                1 - float(distance)
            )
            for chunk, document, distance in results
        ]

    def search(
        self,
        question: str,
        db: Session,
        top_k: int = 20
    ):
        vector_results = self.vector_search(
            question=question,
            db=db,
            top_k=top_k
        )

        keyword_results = keyword_search_service.search(
            question=question,
            db=db,
            top_k=top_k
        )

        scores = defaultdict(float)
        chunks = {}

        for rank, (chunk, document, _) in enumerate(
            vector_results,
            start=1
        ):
            chunk_id = chunk.id

            chunks[chunk_id] = (
                chunk,
                document
            )

            scores[chunk_id] += (
                1 / (RRF_K + rank)
            )

        for rank, (chunk, document, _) in enumerate(
            keyword_results,
            start=1
        ):
            chunk_id = chunk.id

            chunks[chunk_id] = (
                chunk,
                document
            )

            scores[chunk_id] += (
                1 / (RRF_K + rank)
            )

        ranked_results = sorted(
            chunks.items(),
            key=lambda item: scores[item[0]],
            reverse=True
        )

        return [
            (
                chunk,
                document,
                scores[chunk_id]
            )
            for chunk_id, (chunk, document)
            in ranked_results[:top_k]
        ]


hybrid_search_service = HybridSearchService()
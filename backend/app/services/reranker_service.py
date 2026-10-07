from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class RerankerService:

    def __init__(self):
        self.model = CrossEncoder(MODEL_NAME)

    def rerank(
        self,
        question: str,
        chunks: list[tuple],
        top_k: int = 5
    ) -> list[tuple]:

        if not chunks:
            return []

        pairs = [
            (question, chunk.content)
            for chunk, document, vector_similarity in chunks
        ]

        rerank_scores = self.model.predict(pairs)

        reranked = []

        for item, score in zip(chunks, rerank_scores):

            chunk, document, vector_similarity = item

            reranked.append(
                (
                    chunk,
                    document,
                    float(score)
                )
            )

        reranked.sort(
            key=lambda item: item[2],
            reverse=True
        )

        return reranked[:top_k]


reranker_service = RerankerService()
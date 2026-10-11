from sqlalchemy.orm import Session

from app.services.rag_service import retrieve_hybrid_context


def evaluate_retrieval(
    dataset: list[dict],
    db: Session,
    top_k: int = 5
) -> dict:
    total_questions = len(dataset)
    total_hits = 0
    total_precision = 0.0
    total_reciprocal_rank = 0.0
    answerable_questions = 0

    results = []

    for item in dataset:
        question = item["question"]
        expected_document = item["relevant_document"]

        chunks = retrieve_hybrid_context(
            question=question,
            db=db,
            top_k=top_k,
            conversation_history=""
        )

        retrieved_documents = [
            document.filename
            for chunk, document, score in chunks
        ]

        if expected_document is None:
            results.append({
                "id": item["id"],
                "question": question,
                "expected_document": None,
                "retrieved_documents": retrieved_documents,
                "hit": None,
                "precision_at_k": None,
                "reciprocal_rank": None,
                "answerable": False,
            })
            continue

        answerable_questions += 1

        relevant_positions = [
            index + 1
            for index, filename in enumerate(retrieved_documents)
            if filename == expected_document
        ]

        hit = len(relevant_positions) > 0

        precision = (
            len(relevant_positions) / len(retrieved_documents)
            if retrieved_documents
            else 0.0
        )

        reciprocal_rank = (
            1 / relevant_positions[0]
            if relevant_positions
            else 0.0
        )

        if hit:
            total_hits += 1

        total_precision += precision
        total_reciprocal_rank += reciprocal_rank

        results.append({
            "id": item["id"],
            "question": question,
            "expected_document": expected_document,
            "retrieved_documents": retrieved_documents,
            "hit": hit,
            "precision_at_k": precision,
            "reciprocal_rank": reciprocal_rank,
            "answerable": True,
        })

    if answerable_questions:
        hit_rate = total_hits / answerable_questions
        mean_precision = total_precision / answerable_questions
        mrr = total_reciprocal_rank / answerable_questions
    else:
        hit_rate = 0.0
        mean_precision = 0.0
        mrr = 0.0

    return {
        "total_questions": total_questions,
        "answerable_questions": answerable_questions,
        "unanswerable_questions": (
            total_questions - answerable_questions
        ),
        "hits": total_hits,
        "hit_rate": hit_rate,
        "mean_precision_at_k": mean_precision,
        "mrr": mrr,
        "results": results,
    }
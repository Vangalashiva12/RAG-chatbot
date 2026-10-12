
from sqlalchemy.orm import Session

from app.services.rag_service import retrieve_hybrid_context


def evaluate_retrieval(
    dataset: list[dict],
    db: Session,
    top_k: int = 5,
) -> dict:
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    total_questions = len(dataset)
    answerable_questions = 0
    total_hits = 0
    total_precision_at_k = 0.0
    total_returned_precision = 0.0
    total_recall_at_k = 0.0
    total_reciprocal_rank = 0.0

    results = []

    for item in dataset:
        question = item["question"]

        # Support both the current and legacy dataset formats.
        if "relevant_documents" in item:
            relevant_documents = item["relevant_documents"] or []
        else:
            expected_document = item.get("relevant_document")
            relevant_documents = (
                [expected_document]
                if expected_document is not None
                else []
            )

        relevant_documents = set(relevant_documents)

        chunks = retrieve_hybrid_context(
            question=question,
            db=db,
            top_k=top_k,
            conversation_history="",
        )

        # Count each document once, even if multiple chunks are returned.
        retrieved_documents = []
        seen_documents = set()

        for chunk, document, score in chunks:
            filename = document.filename

            if filename not in seen_documents:
                seen_documents.add(filename)
                retrieved_documents.append(filename)

        retrieved_documents = retrieved_documents[:top_k]

        if not relevant_documents:
            results.append({
                "id": item["id"],
                "question": question,
                "expected_documents": [],
                "retrieved_documents": retrieved_documents,
                "hit": None,
                "precision_at_k": None,
                "precision_returned": None,
                "recall_at_k": None,
                "reciprocal_rank": None,
                "answerable": False,
            })
            continue

        answerable_questions += 1

        relevant_positions = [
            index + 1
            for index, filename in enumerate(retrieved_documents)
            if filename in relevant_documents
        ]

        relevant_retrieved_count = len(relevant_positions)
        returned_count = len(retrieved_documents)
        hit = relevant_retrieved_count > 0

        # Fixed-K precision: requested K is always the denominator.
        precision_at_k = relevant_retrieved_count / top_k

        # Returned precision: only documents actually returned count
        # toward the denominator. Zero if no documents were returned.
        precision_returned = (
            relevant_retrieved_count / returned_count
            if returned_count
            else 0.0
        )

        # Recall: fraction of known relevant documents retrieved.
        recall_at_k = (
            relevant_retrieved_count / len(relevant_documents)
        )

        reciprocal_rank = (
            1 / relevant_positions[0]
            if relevant_positions
            else 0.0
        )

        if hit:
            total_hits += 1

        total_precision_at_k += precision_at_k
        total_returned_precision += precision_returned
        total_recall_at_k += recall_at_k
        total_reciprocal_rank += reciprocal_rank

        results.append({
            "id": item["id"],
            "question": question,
            "expected_documents": sorted(relevant_documents),
            "retrieved_documents": retrieved_documents,
            "relevant_documents_retrieved": relevant_retrieved_count,
            "hit": hit,
            "precision_at_k": precision_at_k,
            "precision_returned": precision_returned,
            "recall_at_k": recall_at_k,
            "reciprocal_rank": reciprocal_rank,
            "answerable": True,
        })

    if answerable_questions:
        hit_rate = total_hits / answerable_questions
        mean_precision_at_k = (
            total_precision_at_k / answerable_questions
        )
        mean_returned_precision = (
            total_returned_precision / answerable_questions
        )
        mean_recall_at_k = (
            total_recall_at_k / answerable_questions
        )
        mrr = total_reciprocal_rank / answerable_questions
    else:
        hit_rate = 0.0
        mean_precision_at_k = 0.0
        mean_returned_precision = 0.0
        mean_recall_at_k = 0.0
        mrr = 0.0

    return {
        "total_questions": total_questions,
        "answerable_questions": answerable_questions,
        "unanswerable_questions": (
            total_questions - answerable_questions
        ),
        "hits": total_hits,
        f"hit_rate_at_{top_k}": hit_rate,
        f"precision_at_{top_k}": mean_precision_at_k,
        "mean_precision_returned": mean_returned_precision,
        f"recall_at_{top_k}": mean_recall_at_k,
        "mrr": mrr,
        "results": results,
    }

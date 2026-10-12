
import re
from sqlalchemy.orm import Session

from app.services.rag_service import (
    build_context,
    retrieve_hybrid_context,
)
from app.services.llm_service import bedrock_service


STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were",
    "be", "been", "being", "of", "to", "for", "and",
    "or", "in", "on", "at", "by", "with", "as",
    "it", "its", "this", "that", "from", "after",
    "before", "they", "their", "which", "what",
}


def extract_terms(text: str) -> set[str]:
    """Extract meaningful normalized terms from text."""
    terms = set(re.findall(r"[a-z0-9]+(?:\.[0-9]+)?", text.lower()))

    return {
        term for term in terms
        if term not in STOP_WORDS
    }


def is_answerable(item: dict) -> bool:
    if "relevant_documents" in item:
        return bool(item["relevant_documents"])

    return item.get("relevant_document") is not None


def evaluate_answer_quality(
    dataset: list[dict],
    db: Session,
    top_k: int = 5,
) -> dict:
    results = []

    for item in dataset:
        if not is_answerable(item):
            continue

        question = item["question"]
        expected_answer = item["expected_answer"]

        chunks = retrieve_hybrid_context(
            question=question,
            db=db,
            top_k=top_k,
            conversation_history="",
        )

        context = build_context(chunks)

        answer = bedrock_service.generate_answer(
            question=question,
            context=context,
            conversation_history="No previous conversation history.",
        )

        expected_terms = extract_terms(expected_answer)
        answer_terms = extract_terms(answer)

        matched_terms = sorted(expected_terms & answer_terms)
        missing_terms = sorted(expected_terms - answer_terms)

        coverage = (
            len(matched_terms) / len(expected_terms)
            if expected_terms
            else 0.0
        )

        results.append({
            "id": item["id"],
            "question": question,
            "expected_answer": expected_answer,
            "generated_answer": answer,
            "matched_terms": matched_terms,
            "missing_terms": missing_terms,
            "reference_token_coverage": coverage,
            "context_found": bool(context.strip()),
        })

    total = len(results)

    mean_coverage = (
        sum(r["reference_token_coverage"] for r in results) / total
        if total
        else 0.0
    )

    return {
        "total_questions": total,
        "mean_reference_token_coverage": mean_coverage,
        "results": results,
    }

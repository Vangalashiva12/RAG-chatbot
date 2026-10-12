
from sqlalchemy.orm import Session

from app.services.rag_service import (
    build_context,
    retrieve_hybrid_context,
)
from app.services.llm_service import bedrock_service


REFUSAL_PHRASES = (
    "i couldn't find the answer in the provided documents",
    "i could not find the answer in the provided documents",
    "the provided documents do not specify",
    "the provided documents do not mention",
    "cannot determine from the provided information",
    "cannot determine from the given information",
    "information is not included in the given context",
)


def contains_refusal(answer: str) -> bool:
    normalized_answer = answer.lower()
    return any(
        phrase in normalized_answer
        for phrase in REFUSAL_PHRASES
    )


def is_unanswerable(item: dict) -> bool:
    if "relevant_documents" in item:
        return not item["relevant_documents"]

    return item.get("relevant_document") is None


def evaluate_unanswerable_questions(
    dataset: list[dict],
    db: Session,
    top_k: int = 5,
) -> dict:
    results = []

    for item in dataset:
        if not is_unanswerable(item):
            continue

        question = item["question"]

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

        refused = contains_refusal(answer)

        results.append({
            "id": item["id"],
            "question": question,
            "answer": answer,
            "refused": refused,
            "context_found": bool(context.strip()),
        })

    total = len(results)
    correct_refusals = sum(
        result["refused"] for result in results
    )

    return {
        "total_questions": total,
        "correct_refusals": correct_refusals,
        "unsupported_answers": total - correct_refusals,
        "refusal_rate": (
            correct_refusals / total if total else 0.0
        ),
        "results": results,
    }

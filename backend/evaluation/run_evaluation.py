
from app.core.database import SessionLocal

from evaluation.dataset import EVALUATION_DATASET
from evaluation.retrieval_evaluation import evaluate_retrieval
from evaluation.answer_evaluation import evaluate_unanswerable_questions


def main():
    db = SessionLocal()

    try:
        # ----------------------------------------
        # 1. Retrieval Evaluation
        # ----------------------------------------
        evaluation = evaluate_retrieval(
            dataset=EVALUATION_DATASET,
            db=db,
            top_k=5
        )

        print("\nRAG Retrieval Evaluation")
        print("=" * 45)

        print(f"Total Questions: {evaluation['total_questions']}")
        print(
            f"Answerable Questions: "
            f"{evaluation['answerable_questions']}"
        )
        print(
            f"Unanswerable Questions: "
            f"{evaluation['unanswerable_questions']}"
        )
        print(f"Hits: {evaluation['hits']}")
        print(f"Hit Rate@5: {evaluation['hit_rate']:.2%}")
        print(
            f"Mean Precision@5: "
            f"{evaluation['mean_precision_at_k']:.2%}"
        )
        print(f"MRR: {evaluation['mrr']:.4f}")

        print("\nDetailed Retrieval Results")
        print("-" * 45)

        for result in evaluation["results"]:
            if not result["answerable"]:
                status = "UNANSWERABLE TEST"
            else:
                status = "PASS" if result["hit"] else "FAIL"

            print(f"\n[{status}] Question {result['id']}")
            print(f"Question: {result['question']}")
            print(f"Expected: {result['expected_document']}")
            print(f"Retrieved: {result['retrieved_documents']}")

            if result["answerable"]:
                print(
                    f"Precision@5: "
                    f"{result['precision_at_k']:.2%}"
                )
                print(
                    f"Reciprocal Rank: "
                    f"{result['reciprocal_rank']:.4f}"
                )

        # ----------------------------------------
        # 2. Answer Guardrail Evaluation
        # ----------------------------------------
        answer_evaluation = evaluate_unanswerable_questions(
            dataset=EVALUATION_DATASET,
            db=db,
            top_k=5
        )

        print("\n\nAnswer Guardrail Evaluation")
        print("=" * 45)

        print(
            f"Unanswerable Questions: "
            f"{answer_evaluation['total_questions']}"
        )
        print(
            f"Correct Refusals: "
            f"{answer_evaluation['correct_refusals']}"
        )
        print(
            f"Refusal Rate: "
            f"{answer_evaluation['refusal_rate']:.2%}"
        )

        print("\nDetailed Answer Results")
        print("-" * 45)

        for result in answer_evaluation["results"]:
            status = "PASS" if result["refused"] else "FAIL"

            print(f"\n[{status}] Question {result['id']}")
            print(f"Question: {result['question']}")
            print(f"Answer: {result['answer']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

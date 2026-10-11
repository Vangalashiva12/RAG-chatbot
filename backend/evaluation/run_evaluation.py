from app.core.database import SessionLocal

from evaluation.dataset import EVALUATION_DATASET
from evaluation.retrieval_evaluation import evaluate_retrieval


def main():
    db = SessionLocal()

    try:
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

        print("\nDetailed Results")
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

    finally:
        db.close()


if __name__ == "__main__":
    main()
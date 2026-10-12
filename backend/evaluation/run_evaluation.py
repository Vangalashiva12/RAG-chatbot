
from app.core.database import SessionLocal

from evaluation.dataset import EVALUATION_DATASET
from evaluation.retrieval_evaluation import evaluate_retrieval
from evaluation.answer_evaluation import evaluate_unanswerable_questions
from evaluation.answer_quality_evaluation import evaluate_answer_quality


def main():
    db = SessionLocal()

    try:
        # 1. Retrieval Evaluation
        evaluation = evaluate_retrieval(
            dataset=EVALUATION_DATASET,
            db=db,
            top_k=5,
        )

        print("\nRAG Retrieval Evaluation")
        print("=" * 50)

        print(f"Total Questions: {evaluation['total_questions']}")
        print(f"Answerable Questions: {evaluation['answerable_questions']}")
        print(f"Unanswerable Questions: {evaluation['unanswerable_questions']}")
        print(f"Hits: {evaluation['hits']}")
        print(f"Hit Rate@5: {evaluation['hit_rate_at_5']:.2%}")
        print(f"Precision@5 (fixed K): {evaluation['precision_at_5']:.2%}")
        print(
            "Mean Precision among returned documents: "
            f"{evaluation['mean_precision_returned']:.2%}"
        )
        print(f"Recall@5: {evaluation['recall_at_5']:.2%}")
        print(f"MRR: {evaluation['mrr']:.4f}")

        print("\nDetailed Retrieval Results")
        print("-" * 50)

        for result in evaluation["results"]:
            status = (
                "UNANSWERABLE TEST"
                if not result["answerable"]
                else "PASS" if result["hit"] else "FAIL"
            )

            print(f"\n[{status}] Question {result['id']}")
            print(f"Question: {result['question']}")
            print(f"Expected: {result['expected_documents']}")
            print(f"Retrieved: {result['retrieved_documents']}")

            if result["answerable"]:
                print(f"Precision@5 (fixed K): {result['precision_at_k']:.2%}")
                print(
                    "Precision among returned documents: "
                    f"{result['precision_returned']:.2%}"
                )
                print(f"Recall@5: {result['recall_at_k']:.2%}")
                print(f"Reciprocal Rank: {result['reciprocal_rank']:.4f}")

        # 2. Answer Guardrail Evaluation
        answer_evaluation = evaluate_unanswerable_questions(
            dataset=EVALUATION_DATASET,
            db=db,
            top_k=5,
        )

        print("\n\nAnswer Guardrail Evaluation")
        print("=" * 50)

        print(f"Unanswerable Questions: {answer_evaluation['total_questions']}")
        print(f"Correct Refusals: {answer_evaluation['correct_refusals']}")
        print(f"Unsupported Answers: {answer_evaluation['unsupported_answers']}")
        print(f"Refusal Rate: {answer_evaluation['refusal_rate']:.2%}")

        print("\nDetailed Answer Results")
        print("-" * 50)

        for result in answer_evaluation["results"]:
            status = "PASS" if result["refused"] else "FAIL"

            print(f"\n[{status}] Question {result['id']}")
            print(f"Question: {result['question']}")
            print(f"Context Found: {result['context_found']}")
            print(f"Answer: {result['answer']}")


        # 3. Answer Quality Evaluation
        quality_evaluation = evaluate_answer_quality(
            dataset=EVALUATION_DATASET,
            db=db,
            top_k=5,
        )

        print("\n\nAnswer Quality Evaluation")
        print("=" * 50)

        print(f"Questions Evaluated: {quality_evaluation['total_questions']}")
        print(
            "Mean Reference-Token Coverage: "
            f"{quality_evaluation['mean_reference_token_coverage']:.2%}"
        )

        print("\nDetailed Answer Quality Results")
        print("-" * 50)

        for result in quality_evaluation["results"]:
            print(f"\nQuestion {result['id']}: {result['question']}")
            print(f"Expected Answer: {result['expected_answer']}")
            print(f"Generated Answer: {result['generated_answer']}")
            print(f"Matched Terms: {result['matched_terms']}")
            print(f"Missing Terms: {result['missing_terms']}")
            print(
                "Reference-Token Coverage: "
                f"{result['reference_token_coverage']:.2%}"
            )
            print(f"Context Found: {result['context_found']}")

    finally:
        db.close()


if __name__ == "__main__":
    main()

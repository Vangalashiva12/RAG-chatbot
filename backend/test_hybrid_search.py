from app.core.database import SessionLocal
from app.services.hybrid_search_service import hybrid_search_service


db = SessionLocal()

try:
    results = hybrid_search_service.search(
        question="What is FastAPI used for?",
        db=db,
        top_k=5
    )

    print("\n===== HYBRID SEARCH RESULTS =====\n")

    if not results:
        print("No results found.")

    for rank, (chunk, document, score) in enumerate(
        results,
        start=1
    ):
        print(f"Rank: {rank}")
        print(f"Document ID: {document.id}")
        print(f"Filename: {document.filename}")
        print(f"Chunk ID: {chunk.id}")
        print(f"Chunk Index: {chunk.chunk_index}")
        print(f"RRF Score: {score}")
        print(f"Content: {chunk.content}")
        print("-" * 80)

finally:
    db.close()
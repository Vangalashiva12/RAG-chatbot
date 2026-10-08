from app.core.database import SessionLocal
from app.services.keyword_search_service import keyword_search_service


db = SessionLocal()

try:
    results = keyword_search_service.search(
        question="What is FastAPI used for?",
        db=db,
        top_k=5
    )

    print("\n===== KEYWORD SEARCH RESULTS =====\n")

    if not results:
        print("No results found.")

    for chunk, document, score in results:
        print(f"Document ID: {document.id}")
        print(f"Filename: {document.filename}")
        print(f"Chunk ID: {chunk.id}")
        print(f"Chunk Index: {chunk.chunk_index}")
        print(f"Keyword Score: {score}")
        print(f"Content: {chunk.content}")
        print("-" * 80)

finally:
    db.close()
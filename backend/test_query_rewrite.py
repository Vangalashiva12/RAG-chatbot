from app.services.query_rewrite_service import query_rewrite_service


conversation_history = """
User: What is FastAPI used for?
Assistant: FastAPI is used as the backend API for the Enterprise RAG Chatbot.

User: What database does the chatbot use?
Assistant: PostgreSQL is used as the relational database.
"""


questions = [
    "Why is it useful here?",
    "What does it do?",
    "Why is that important?",
    "How does it work?",
    "What about the previous one?"
]


print("\n===== QUERY REWRITE TESTS =====\n")


for question in questions:

    rewritten_query = query_rewrite_service.rewrite_query(
        question=question,
        conversation_history=conversation_history
    )

    print(f"Original:  {question}")
    print(f"Rewritten: {rewritten_query}")
    print("-" * 80)
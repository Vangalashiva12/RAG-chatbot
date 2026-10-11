EVALUATION_DATASET = [
    {
        "id": 1,
        "question": "What is FastAPI used for?",
        "expected_answer": (
            "FastAPI is being used as the backend API."
        ),
        "relevant_document": "test_document.txt",
    },
    {
        "id": 2,
        "question": "Which database is used by the chatbot?",
        "expected_answer": (
            "PostgreSQL is being used as the relational database."
        ),
        "relevant_document": "test_document.txt",
    },
    {
        "id": 3,
        "question": "What is the purpose of doc1?",
        "expected_answer": (
            "It is used to test document upload, processing, "
            "chunking, and embeddings."
        ),
        "relevant_document": "doc1.txt",
    },
    {
        "id": 4,
        "question": "Which document mentions text extraction?",
        "expected_answer": (
            "test_document.txt mentions text extraction."
        ),
        "relevant_document": "test_document.txt",
    },
    {
        "id": 5,
        "question": "What is the chatbot going to use embeddings for?",
        "expected_answer": (
            "Embeddings are one of the planned uses of the "
            "test document in the Enterprise RAG Chatbot."
        ),
        "relevant_document": "test_document.txt",
    },
    {
        "id": 6,
        "question": "Which document mentions chunking and embeddings?",
        "expected_answer": (
            "Both test_document.txt and doc1.txt mention chunking "
            "and embeddings."
        ),
        "relevant_document": "doc1.txt",
    },
    {
        "id": 7,
        "question": "What is the chatbot's frontend framework?",
        "expected_answer": (
            "The provided documents do not specify a frontend framework."
        ),
        "relevant_document": None,
    },
    {
        "id": 8,
        "question": "Which cloud provider hosts the chatbot?",
        "expected_answer": (
            "The provided documents do not specify a cloud provider."
        ),
        "relevant_document": None,
    },
    {
        "id": 9,
        "question": "What retrieval approach is mentioned in the test document?",
        "expected_answer": (
            "Retrieval-Augmented Generation is listed as a planned use."
        ),
        "relevant_document": "test_document.txt",
    },
    {
        "id": 10,
        "question": "What tasks will doc1 help test?",
        "expected_answer": (
            "Document upload, processing, chunking, and embeddings."
        ),
        "relevant_document": "doc1.txt",
    },
]
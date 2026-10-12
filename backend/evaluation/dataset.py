
EVALUATION_DATASET = [
    # Original technical-document questions
    {
        "id": 1,
        "question": "What is FastAPI used for?",
        "expected_answer": "FastAPI is used as the backend API.",
        "relevant_documents": ["test_document.txt"],
    },
    {
        "id": 2,
        "question": "Which database is used by the chatbot?",
        "expected_answer": "PostgreSQL is used as the relational database.",
        "relevant_documents": ["test_document.txt"],
    },
    {
        "id": 3,
        "question": "What is the purpose of doc1?",
        "expected_answer": (
            "It is used to test document upload, processing, "
            "chunking, and embeddings."
        ),
        "relevant_documents": ["doc1.txt"],
    },
    {
        "id": 4,
        "question": "Which document mentions text extraction?",
        "expected_answer": "test_document.txt mentions text extraction.",
        "relevant_documents": ["test_document.txt"],
    },
    {
        "id": 5,
        "question": "What is the chatbot going to use embeddings for?",
        "expected_answer": (
            "Embeddings are one of the planned uses of the "
            "Enterprise RAG Chatbot test document."
        ),
        "relevant_documents": ["test_document.txt"],
    },
    {
        "id": 6,
        "question": "Which document mentions chunking and embeddings?",
        "expected_answer": (
            "Both test_document.txt and doc1.txt mention "
            "chunking and embeddings."
        ),
        "relevant_documents": ["test_document.txt", "doc1.txt"],
    },
    {
        "id": 7,
        "question": "What is the chatbot's frontend framework?",
        "expected_answer": (
            "The provided documents do not specify the frontend framework."
        ),
        "relevant_documents": [],
    },
    {
        "id": 8,
        "question": "Which cloud provider hosts the chatbot?",
        "expected_answer": (
            "The provided documents do not specify a cloud provider."
        ),
        "relevant_documents": [],
    },
    {
        "id": 9,
        "question": (
            "What retrieval approach is mentioned in the test document?"
        ),
        "expected_answer": (
            "Retrieval-Augmented Generation is listed as a planned use."
        ),
        "relevant_documents": ["test_document.txt"],
    },
    {
        "id": 10,
        "question": "What tasks will doc1 help test?",
        "expected_answer": (
            "Document upload, processing, chunking, and embeddings."
        ),
        "relevant_documents": ["doc1.txt"],
    },

    # New questions grounded in 23.txt: Employee Handbook
    {
        "id": 11,
        "question": "Where is NovaTech Solutions headquartered?",
        "expected_answer": "Austin, Texas.",
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 12,
        "question": "How many employees does NovaTech Solutions have?",
        "expected_answer": (
            "The company has 240 employees across five departments."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 13,
        "question": "What are the standard working hours?",
        "expected_answer": (
            "Monday through Friday, from 9:00 AM to 5:00 PM Central Time."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 14,
        "question": "How many annual PTO days do full-time employees receive?",
        "expected_answer": (
            "15 days of annual PTO after completing the probationary period."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 15,
        "question": "How many days per week can eligible employees work remotely?",
        "expected_answer": (
            "Up to three days per week with manager approval."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 16,
        "question": "What is the annual professional development allowance?",
        "expected_answer": (
            "$1,200 per full-time employee, subject to manager approval."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 17,
        "question": "What is the hotel reimbursement limit?",
        "expected_answer": (
            "$220 per night before taxes, unless a manager approves "
            "an exception in advance."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 18,
        "question": (
            "How quickly must employees report lost company devices, "
            "and when must replaced equipment be returned?"
        ),
        "expected_answer": (
            "Lost or stolen devices must be reported within one hour "
            "of discovery. Replaced equipment must be returned within "
            "five business days of receiving the replacement."
        ),
        "relevant_documents": ["23.txt"],
    },
    {
        "id": 19,
        "question": "How many days of paid parental leave does the company provide?",
        "expected_answer": (
            "The employee handbook does not specify a paid parental "
            "leave allowance."
        ),
        "relevant_documents": [],
    },
    {
        "id": 20,
        "question": (
            "Can employees work remotely five days a week under the "
            "standard policy?"
        ),
        "expected_answer": (
            "The standard policy permits up to three remote days per "
            "week with manager approval. Exceptions are not specified "
            "in the document."
        ),
        "relevant_documents": ["23.txt"],
    },
]

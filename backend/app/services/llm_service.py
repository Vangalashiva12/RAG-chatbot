from google import genai

from app.core.config import settings


class GeminiService:
    def __init__(self):
        self.client = genai.Client(
            api_key=settings.gemini_api_key
        )

    def generate_answer(
        self,
        question: str,
        context: str
    ) -> str:

        prompt = f"""
You are an enterprise RAG assistant.

Answer the user's question using ONLY the provided context.

If the answer cannot be found in the context, say:
"I couldn't find the answer in the provided documents."

Do not invent information.

Context:
--------------------
{context}
--------------------

Question:
{question}

Answer:
"""

        response = self.client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt
        )

        return response.text


gemini_service = GeminiService()
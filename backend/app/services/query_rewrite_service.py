import re

from app.services.llm_service import bedrock_service


class QueryRewriteService:

    def rewrite_query(
        self,
        question: str,
        conversation_history: str
    ) -> str:

        if not conversation_history.strip():
            return question

        prompt = f"""
You are a search query rewriting system for an enterprise RAG chatbot.

Your task is to rewrite the user's current question into a
standalone search query that can be used to retrieve relevant
documents.

Use the conversation history only to resolve references such as:
- it
- this
- that
- they
- previous one
- the above
- here

Rules:

- Preserve the user's original intent.
- Include important context from the conversation when necessary.
- Do not answer the question.
- Do not add information that is not present in the conversation.
- Return ONLY the rewritten search query.
- Do not use Markdown.
- Do not use quotation marks.
- Do not provide explanations.
- Keep it concise.

Conversation History:
--------------------
{conversation_history}
--------------------

Current User Question:
--------------------
{question}
--------------------

Standalone Search Query:
"""

        rewritten_query = bedrock_service.generate_simple_answer(
            prompt
        ).strip()

        rewritten_query = re.sub(
            r"[*_`]",
            "",
            rewritten_query
        )

        rewritten_query = rewritten_query.strip(
            "\"'"
        )

        return rewritten_query


query_rewrite_service = QueryRewriteService()
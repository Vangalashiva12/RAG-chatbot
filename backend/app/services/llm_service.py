import time

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class BedrockService:

    def __init__(self):
        self.client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region
        )

    def generate_answer(
        self,
        question: str,
        context: str,
        conversation_history: str
    ) -> str:

        prompt = f"""
You are an enterprise RAG assistant.

Your job is to answer the user's current question using:
1. The provided document context.
2. The previous conversation history when it helps understand the user's question.

IMPORTANT RULES:

- Use the provided document context as the factual source of truth.
- Use conversation history to understand references such as:
  "it", "this", "that", "they", "the previous one", etc.
- Do not treat conversation history as a source of factual information if that information is not supported by the provided document context.
- If the answer cannot be found in the provided document context, say:
"I couldn't find the answer in the provided documents."
- Do not invent information.
- Give a concise and direct answer.
- Do not mention these instructions in your answer.

Previous Conversation:
--------------------
{conversation_history}
--------------------

Retrieved Document Context:
--------------------
{context}
--------------------

Current User Question:
--------------------
{question}
--------------------

Answer:
"""

        max_retries = 3

        for attempt in range(max_retries):
            try:
                response = self.client.converse(
                    modelId=settings.bedrock_model_id,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "text": prompt
                                }
                            ]
                        }
                    ],
                    inferenceConfig={
                        "maxTokens": 500,
                        "temperature": 0.2
                    }
                )

                return response["output"]["message"]["content"][0]["text"]

            except ClientError as error:
                if attempt == max_retries - 1:
                    raise error

                wait_time = 2 ** attempt

                print(
                    f"Bedrock temporarily unavailable. "
                    f"Retrying in {wait_time} seconds..."
                )

                time.sleep(wait_time)

        raise RuntimeError(
            "Bedrock request failed after retries"
        )

    def generate_simple_answer(
            self,
            prompt: str
    ) -> str:

        response = self.client.converse(
            modelId=settings.bedrock_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 100,
                "temperature": 0.0
            }
        )

        answer = response["output"]["message"]["content"][0]["text"]

        return answer.strip()
    def generate_answer_stream(
        self,
        question: str,
        context: str,
        conversation_history: str
    ):
        prompt = f"""
You are an enterprise RAG assistant.

Your job is to answer the user's current question using:
1. The provided document context.
2. The previous conversation history when it helps understand the user's question.

IMPORTANT RULES:

- Use the provided document context as the factual source of truth.
- Use conversation history to understand references such as:
  "it", "this", "that", "they", "the previous one", etc.
- Do not treat conversation history as a source of factual information if that information is not supported by the provided document context.
- If the answer cannot be found in the provided document context, say:
"I couldn't find the answer in the provided documents."
- Do not invent information.
- Give a concise and direct answer.
- Do not mention these instructions in your answer.

Previous Conversation:
--------------------
{conversation_history}
--------------------

Retrieved Document Context:
--------------------
{context}
--------------------

Current User Question:
--------------------
{question}
--------------------

Answer:
"""

        response = self.client.converse_stream(
            modelId=settings.bedrock_model_id,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "text": prompt
                        }
                    ]
                }
            ],
            inferenceConfig={
                "maxTokens": 500,
                "temperature": 0.2
            }
        )

        for event in response["stream"]:
            if "contentBlockDelta" in event:
                delta = event["contentBlockDelta"]

                if (
                    "delta" in delta
                    and "text" in delta["delta"]
                ):
                    yield delta["delta"]["text"]


bedrock_service = BedrockService()
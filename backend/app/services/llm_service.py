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

        raise RuntimeError("Bedrock request failed after retries")


bedrock_service = BedrockService()
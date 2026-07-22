from openai import AsyncOpenAI

from app.config import settings


class LLMClient:

    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        self.model = settings.OPENAI_MODEL

    async def chat(
        self,
        messages: list[dict],
        tools=None
    ):

        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools

        response = await (
            self.client.chat.completions.create(
                **kwargs
            )
        )

        return response

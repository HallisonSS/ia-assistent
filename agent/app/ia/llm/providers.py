from abc import ABC, abstractmethod

from app.llm.client import OpenAIClient


class LLMProvider(ABC):

    @abstractmethod
    async def chat(
        self,
        messages: list[dict]
    ) -> str:
        pass


class OpenAIProvider(LLMProvider):

    def __init__(self):
        self.client = OpenAIClient()

    async def chat(
        self,
        messages: list[dict]
    ) -> str:

        return await self.client.chat(
            messages
        )


def get_llm_provider() -> LLMProvider:

    return OpenAIProvider()

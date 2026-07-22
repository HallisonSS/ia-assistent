from openai import AsyncOpenAI

from app.config import settings


class STTService:

    def __init__(self):

        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        self.model = (
            settings.OPENAI_STT_MODEL
        )

    async def transcribe(
        self,
        audio_file
    ):

        result = await (
            self.client.audio
            .transcriptions.create(
                model=self.model,
                file=audio_file
            )
        )

        return result.text

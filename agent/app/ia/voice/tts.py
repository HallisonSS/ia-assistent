from pathlib import Path

from openai import AsyncOpenAI

from app.config import settings


class TTSService:

    def __init__(self):

        self.client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY
        )

        self.model = (
            settings.OPENAI_TTS_MODEL
        )

        self.voice = (
            settings.OPENAI_TTS_VOICE
        )

    async def synthesize(
        self,
        text: str,
        output_file: str
    ):

        speech = await (
            self.client.audio
            .speech.create(
                model=self.model,
                voice=self.voice,
                input=text
            )
        )

        speech.stream_to_file(
            Path(output_file)
        )

        return output_file

from pydantic_settings import BaseSettings


class Settings(BaseSettings):

    OPENAI_API_KEY: str

    OPENAI_MODEL: str = "gpt-4o-mini"

    OPENAI_STT_MODEL: str = "whisper-1"

    OPENAI_TTS_MODEL: str = "tts-1"

    OPENAI_TTS_VOICE: str = "alloy"

    REDIS_HOST: str = "redis"

    REDIS_PORT: int = 6379

    ALERTS_STREAM: str = "alerts_stream"


settings = Settings()

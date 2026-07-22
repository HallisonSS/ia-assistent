import os
from dataclasses import dataclass


@dataclass
class Settings:
    openai_api_key: str
    openai_model: str
    openai_stt_model: str
    openai_tts_model: str
    openai_tts_voice: str

    database_url: str
    redis_url: str

    app_env: str
    log_level: str


def load_settings() -> Settings:
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY não configurada."
        )

    return Settings(
        openai_api_key=api_key,
        openai_model=os.getenv(
            "OPENAI_MODEL",
            "gpt-4o-mini"
        ),
        openai_stt_model=os.getenv(
            "OPENAI_STT_MODEL",
            "whisper-1"
        ),
        openai_tts_model=os.getenv(
            "OPENAI_TTS_MODEL",
            "tts-1"
        ),
        openai_tts_voice=os.getenv(
            "OPENAI_TTS_VOICE",
            "alloy"
        ),
        database_url=os.getenv(
            "DATABASE_URL"
        ),
        redis_url=os.getenv(
            "REDIS_URL"
        ),
        app_env=os.getenv(
            "APP_ENV",
            "development"
        ),
        log_level=os.getenv(
            "LOG_LEVEL",
            "INFO"
        ),
    )

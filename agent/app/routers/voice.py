from fastapi import (
    APIRouter,
    UploadFile,
    File
)

from app.ai.voice.stt import (
    STTService
)


router = APIRouter(
    prefix="/voice",
    tags=["Voice"]
)


stt = STTService()


@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...)
):

    result = await stt.transcribe(
        audio.file
    )

    return {
        "text": result
    }

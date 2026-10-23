import os
import json
import redis.asyncio as redis
from fastapi import FastAPI
from pydantic import BaseModel

from app.admin import router as admin_router
from app.routers.voice import router as voice_router

app = FastAPI(title="Assistente-IA API")
app.include_router(admin_router)
app.include_router(voice_router)

r = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)
ALERTS_STREAM = os.getenv("ALERTS_STREAM", "alerts_stream")
ACTIONS_STREAM = os.getenv("ACTIONS_STREAM", "actions_stream")


class Alert(BaseModel):
    status: str | None = None
    labels: dict = {}
    annotations: dict = {}
    startsAt: str | None = None
    endsAt: str | None = None


class AlertmanagerWebhook(BaseModel):
    version: str
    groupKey: str
    status: str
    receiver: str
    groupLabels: dict
    commonLabels: dict
    commonAnnotations: dict
    externalURL: str
    alerts: list[Alert]


class ActionRequest(BaseModel):
    action: str
    params: dict
    requested_by: str | None = "api"


@app.post("/alerts")
async def alerts(payload: AlertmanagerWebhook):
    for a in payload.alerts:
        await r.xadd(ALERTS_STREAM, {
            "status": a.status or "",
            "labels": json.dumps(a.labels),
            "annotations": json.dumps(a.annotations),
            "startsAt": a.startsAt or "",
        })
    return {"ok": True}


@app.post("/actions")
async def actions(req: ActionRequest):
    await r.xadd(ACTIONS_STREAM, {
        "action": req.action,
        "params": json.dumps(req.params),
        "requested_by": req.requested_by,
    })
    return {"queued": True}


@app.get("/health")
async def health():
    await r.ping()
    return {"status": "ok"}

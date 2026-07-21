from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import os
import redis
import json

r = redis.Redis(host=os.getenv("REDIS_HOST","redis"), port=int(os.getenv("REDIS_PORT","6379")), decode_responses=True)
ALERTS_STREAM = os.getenv("ALERTS_STREAM","alerts_stream")

app = FastAPI(title="Assistente-IA API")

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

@app.post("/alerts")
async def alerts(payload: AlertmanagerWebhook):
    # Publica cada alerta no stream
    for a in payload.alerts:
        r.xadd(ALERTS_STREAM, {
            "status": a.status or "",
            "labels": json.dumps(a.labels),
            "annotations": json.dumps(a.annotations),
            "startsAt": a.startsAt or "",
        })
    return {"ok": True}

class ActionRequest(BaseModel):
    action: str
    params: dict
    requested_by: str | None = "api"

ACTIONS_STREAM = os.getenv("ACTIONS_STREAM","actions_stream")

@app.post("/actions")
async def actions(req: ActionRequest):
    # Cria solicitação de ação (pode exigir aprovação)
    r.xadd(ACTIONS_STREAM, {"action": req.action, "params": json.dumps(req.params), "requested_by": req.requested_by})
    return {"queued": True}

@app.get("/health")
def health():
    return {"status":"ok"}

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import psycopg, os, json

router = APIRouter(prefix="/admin", tags=["admin"])
DB_DSN = os.getenv("DB_DSN","postgresql://assist:strong_password_here@postgres:5432/assistdb")

class Decision(BaseModel):
  approval_id: int
  approve: bool
  decided_by: str

@router.get("/approvals")
def list_approvals():
  with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
    cur.execute("SELECT id, requested_by, action, params, status, created_at FROM approvals WHERE status='pending' ORDER BY id DESC")
    rows = cur.fetchall()
    return [{"id":r[0],"requested_by":r[1],"action":r[2],"params":r[3],"status":r[4],"created_at":str(r[5])} for r in rows]

@router.post("/approvals/decide")
def decide(d: Decision):
  with psycopg.connect(DB_DSN) as conn, conn.cursor() as cur:
    cur.execute("SELECT action, params, status FROM approvals WHERE id=%s", (d.approval_id,))
    row = cur.fetchone()
    if not row: raise HTTPException(404, "not found")
    action, params, status = row
    if status != "pending": raise HTTPException(400, "already decided")
    new_status = "approved" if d.approve else "rejected"
    cur.execute("UPDATE approvals SET status=%s, decided_by=%s, decided_at=now() WHERE id=%s", (new_status, d.decided_by, d.approval_id))
    conn.commit()
    return {"updated": True, "status": new_status}

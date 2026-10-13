import os, json, subprocess, shlex, time, sys
from multiprocessing import Process

import redis
import psycopg
import httpx

# ---------- Configuração (tudo via ambiente) ----------
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

ALERTS_STREAM = os.getenv("ALERTS_STREAM", "alerts_stream")
DECISIONS_STREAM = os.getenv("DECISIONS_STREAM", "decisions_stream")
ACTIONS_STREAM = os.getenv("ACTIONS_STREAM", "actions_stream")
GROUP = os.getenv("WORKER_GROUP", "assist_group")
CONSUMER = os.getenv("WORKER_CONSUMER", "worker")

DB_DSN = os.environ["DB_DSN"]  # sem default: falha se faltar

USE_OLLAMA = os.getenv("USE_OLLAMA", "true") == "true"
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ollama:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:1.3b")
OPENAI_URL = os.getenv("OPENAI_BASE_URL", "")
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")

# Prefixo do executor seguro. Precisa existir onde o worker roda (host).
SAFE_RUN = os.getenv("SAFE_RUN", "sudo /usr/local/bin/assist-safe-run")

POLICY_SAFE_ACTIONS = {
    "restart_service": {"cmd": SAFE_RUN + " systemctl restart {service}", "approval": "maybe"},
    "start_service":   {"cmd": SAFE_RUN + " systemctl start {service}",   "approval": "maybe"},
    "stop_service":    {"cmd": SAFE_RUN + " systemctl stop {service}",    "approval": "admin"},
    "apt_update":      {"cmd": SAFE_RUN + " apt update",                  "approval": "operator"},
    "apt_upgrade":     {"cmd": SAFE_RUN + " apt upgrade -y",              "approval": "admin"},
    "ufw_allow":       {"cmd": SAFE_RUN + " ufw allow {port}/tcp",        "approval": "admin"},
}

ALLOWED_SERVICES = {"nginx", "apache2", "ssh", "docker"}


# ---------- Infra ----------
def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


def get_conn(retries=30):
    for i in range(retries):
        try:
            return psycopg.connect(DB_DSN)
        except psycopg.OperationalError as e:
            print(f"[db] aguardando postgres ({i+1}/{retries}): {e}", flush=True)
            time.sleep(2)
    raise RuntimeError("Não foi possível conectar ao Postgres")


def ensure_group(r, stream):
    try:
        r.xgroup_create(name=stream, groupname=GROUP, id="0-0", mkstream=True)
    except redis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise


def log_audit(conn, event_type, source, input_d=None, decision_d=None, command=None,
              stdout=None, stderr=None, exit_code=None, user_context=None):
    with conn.cursor() as cur:
        cur.execute("""
          INSERT INTO audit_log(event_type,source,input,decision,command,stdout,stderr,exit_code,user_context)
          VALUES(%s,%s,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s)
        """, (
            event_type, source,
            json.dumps(input_d) if input_d else None,
            json.dumps(decision_d) if decision_d else None,
            command, stdout, stderr, exit_code, user_context
        ))
    conn.commit()


# ---------- LLM / decisão ----------
def llm_plan(prompt):
    if USE_OLLAMA:
        data = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
        resp = httpx.post(f"{OLLAMA_URL}/api/generate", json=data, timeout=60)
        resp.raise_for_status()
        return resp.json().get("response", "")
    headers = {"Authorization": f"Bearer {OPENAI_KEY}"}
    data = {"model": "gpt-4o-mini", "messages": [
        {"role": "system", "content": "You are a remediation planner. Output JSON."},
        {"role": "user", "content": prompt}]}
    resp = httpx.post(f"{OPENAI_URL}/v1/chat/completions", headers=headers, json=data, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


def decide_remediation(alert):
    labels = json.loads(alert.get("labels", "{}"))
    annotations = json.loads(alert.get("annotations", "{}"))
    hint = annotations.get("summary", "") or annotations.get("description", "")

    if "InstanceDown" in labels.get("alertname", ""):
        return {"action": "restart_service", "params": {"service": "apache2"},
                "reason": "Instance down - tentar reiniciar apache2"}

    prompt = f"""
Você é um assistente de SRE. Recebeu um alerta com labels={labels} e hint="{hint}".
Proponha UMA ação canônica no formato JSON: {{"action":"<uma_das_chaves_de_POLICY>","params":{{...}},"reason":"..."}}.
Ações válidas: {list(POLICY_SAFE_ACTIONS.keys())}.
Se não tiver certeza, use "restart_service" com "service":"<nome>" baseado no hint.
Responda apenas o JSON.
"""
    try:
        raw = llm_plan(prompt).strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        plan = json.loads(raw)
        if not isinstance(plan, dict):
            raise ValueError("plano não é objeto")
    except Exception:
        plan = {"action": "restart_service", "params": {"service": "nginx"}, "reason": "fallback"}
    return plan


# ---------- Política ----------
def needs_approval(action_key):
    level = POLICY_SAFE_ACTIONS.get(action_key, {}).get("approval", "admin")
    return level in ("admin", "operator")


def validate_params(action_key, params):
    if action_key not in POLICY_SAFE_ACTIONS:
        raise ValueError(f"Ação desconhecida: {action_key}")
    if not isinstance(params, dict):
        raise ValueError("params inválido")
    if action_key in ("restart_service", "start_service", "stop_service"):
        svc = params.get("service", "")
        if svc not in ALLOWED_SERVICES:
            raise ValueError(f"Serviço não permitido: {svc}")
    if action_key == "ufw_allow":
        port = int(params.get("port", 0))
        if port < 1024 or port > 65535:
            raise ValueError("Porta inválida")
        params["port"] = port
    return True


def run_command(cmd):
    # sem shell=True: evita injeção via parâmetros
    try:
        proc = subprocess.run(shlex.split(cmd), capture_output=True, text=True, timeout=120)
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def build_cmd(action, params):
    return POLICY_SAFE_ACTIONS[action]["cmd"].format(**params)


def create_approval(conn, requested_by, action, params):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO approvals(requested_by, action, params, status) VALUES(%s,%s,%s::jsonb,'pending')",
            (requested_by, action, json.dumps(params)))
    conn.commit()


# ---------- Loops (um processo cada, com conexões próprias) ----------
def process_alerts():
    r, conn = get_redis(), get_conn()
    ensure_group(r, ALERTS_STREAM)
    while True:
        resp = r.xreadgroup(GROUP, CONSUMER, {ALERTS_STREAM: ">"}, count=1, block=5000)
        if not resp:
            continue
        for _, messages in resp:
            for msg_id, fields in messages:
                try:
                    plan = decide_remediation(fields)
                    r.xadd(DECISIONS_STREAM, {"plan": json.dumps(plan), "source": "alert"})
                    log_audit(conn, "decision", "worker", input_d=fields, decision_d=plan)

                    action, params = plan["action"], plan.get("params", {})
                    validate_params(action, params)
                    if needs_approval(action):
                        create_approval(conn, "system", action, params)
                    else:
                        cmd = build_cmd(action, params)
                        code, out, err = run_command(cmd)
                        log_audit(conn, "execution", "worker", decision_d=plan,
                                  command=cmd, stdout=out, stderr=err, exit_code=code)
                except Exception as e:
                    conn.rollback()
                    log_audit(conn, "decision", "worker", input_d=fields, decision_d={"error": str(e)})
                r.xack(ALERTS_STREAM, GROUP, msg_id)


def process_actions():
    r, conn = get_redis(), get_conn()
    ensure_group(r, ACTIONS_STREAM)
    while True:
        resp = r.xreadgroup(GROUP, CONSUMER, {ACTIONS_STREAM: ">"}, count=1, block=5000)
        if not resp:
            continue
        for _, messages in resp:
            for msg_id, fields in messages:
                req_by = fields.get("requested_by", "api")
                try:
                    action = fields["action"]
                    params = json.loads(fields["params"])
                    validate_params(action, params)
                    if needs_approval(action):
                        create_approval(conn, req_by, action, params)
                        log_audit(conn, "decision", "api", input_d=fields,
                                  decision_d={"approval": "pending"}, user_context=req_by)
                    else:
                        cmd = build_cmd(action, params)
                        code, out, err = run_command(cmd)
                        log_audit(conn, "execution", "api",
                                  decision_d={"action": action, "params": params},
                                  command=cmd, stdout=out, stderr=err, exit_code=code,
                                  user_context=req_by)
                except Exception as e:
                    conn.rollback()
                    log_audit(conn, "decision", "api", input_d=fields,
                              decision_d={"error": str(e)}, user_context=req_by)
                r.xack(ACTIONS_STREAM, GROUP, msg_id)


def process_approved():
    conn = get_conn()
    while True:
        # "claim" atômico: marca como reconciled e devolve as linhas
        with conn.cursor() as cur:
            cur.execute("""
              UPDATE approvals SET status='reconciled'
              WHERE id IN (
                SELECT id FROM approvals WHERE status='approved'
                ORDER BY id LIMIT 10 FOR UPDATE SKIP LOCKED)
              RETURNING id, action, params
            """)
            rows = cur.fetchall()
        conn.commit()

        for id_, action, params in rows:
            p = params if isinstance(params, dict) else json.loads(params)  # jsonb já vem como dict
            try:
                validate_params(action, p)
                cmd = build_cmd(action, p)
                code, out, err = run_command(cmd)
                log_audit(conn, "execution", "approval",
                          decision_d={"id": id_, "action": action, "params": p},
                          command=cmd, stdout=out, stderr=err, exit_code=code)
            except Exception as e:
                conn.rollback()
                log_audit(conn, "execution", "approval",
                          decision_d={"id": id_, "error": str(e)})
        time.sleep(5)


if __name__ == "__main__":
    targets = [process_alerts, process_actions, process_approved]
    procs = [Process(target=t, name=t.__name__) for t in targets]
    for p in procs:
        p.start()
    try:
        # se qualquer processo morrer, encerra tudo para o restart policy reiniciar
        while all(p.is_alive() for p in procs):
            time.sleep(2)
    except KeyboardInterrupt:
        pass
    for p in procs:
        if p.is_alive():
            p.terminate()
    sys.exit(1)

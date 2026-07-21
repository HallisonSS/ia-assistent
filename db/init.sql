CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username TEXT UNIQUE NOT NULL,
  role TEXT NOT NULL CHECK (role IN ('admin','operator','viewer')),
  created_at TIMESTAMP DEFAULT now()
);

CREATE TABLE IF NOT EXISTS approvals (
  id SERIAL PRIMARY KEY,
  requested_by TEXT NOT NULL,
  action TEXT NOT NULL,
  params JSONB,
  status TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
  created_at TIMESTAMP DEFAULT now(),
  decided_by TEXT,
  decided_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_log (
  id SERIAL PRIMARY KEY,
  event_type TEXT NOT NULL,            -- 'monitoring','decision','execution'
  source TEXT,                         -- 'alertmanager','api','worker'
  input JSONB,                         -- dados recebidos
  decision JSONB,                      -- plano/decisão
  command TEXT,                        -- comando executado (se houver)
  stdout TEXT,
  stderr TEXT,
  exit_code INT,
  created_at TIMESTAMP DEFAULT now(),
  user_context TEXT                    -- usuário que acionou (se houver)
);

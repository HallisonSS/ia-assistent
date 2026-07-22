# ai-assistent
Objetivo: o assistente deve:

Monitorar recursos (CPU, RAM, disco, processos, serviços, portas).
Ler logs e alertas.
Decidir ações de remediação com base em regras e/ou LLM.
Executar ações pré-aprovadas e registrar tudo (entrada, decisão, comando, saída).
Solicitar aprovação humana quando necessário (RBAC).
Expor API e painel.
Componentes:

observabilidade/: Prometheus, Alertmanager, Grafana, Loki, Promtail, Node Exporter
bus/: Redis
agent/: FastAPI (API), Celery worker (tarefas), Regras/Políticas, Conectores LLM
executor/: Playbooks Ansible, scripts shell wrappers, whitelists sudoers
db/: Postgres (RBAC, auditoria, estado)
llm/: Ollama (modelos locais) ou conector externo
Fluxo:

Exporters e Promtail enviam métricas/logs.
Alertmanager gera alerta → publica em Redis.
Worker lê o evento, aplica políticas e, quando indicado, consulta LLM para plano de ação.
Executor aplica ação segura (whitelist) e grava auditoria no Postgres.
API expõe status, aprovações pendentes e histórico.
Grafana dashboards e anotações.
2) Preparação do servidor Ubuntu
Ubuntu 22.04 LTS ou 24.04 LTS
Usuário com sudo sem senha? Não. Usaremos sudo com regras específicas.
Atualize e instale base:

sudo apt update && sudo apt -y upgrade
sudo apt install -y git curl wget python3-pip python3-venv build-essential ufw

Firewall básico (ajuste portas conforme necessidade):
sudo ufw allow OpenSSH
sudo ufw allow 3000/tcp # Grafana
sudo ufw allow 9090/tcp # Prometheus
sudo ufw allow 9093/tcp # Alertmanager
sudo ufw allow 8000/tcp # API do agente
sudo ufw enable

Docker e Compose:
curl -fsSL get.docker.com | sudo sh

sudo usermod -aG docker $USER newgrp docker
sudo curl -L "github.com" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker --version && docker-compose version

3) Estrutura do repositório
Crie diretórios:

mkdir -p ai-assistente/{observability,agent,executor,db,llm,bus,configs,deploy}
cd ai-assistente
git init

Suba o Postgres e aplique o schema:
docker run --rm -v $(pwd)/db:/mnt -e PGPASSWORD=strong_password_here --network host postgres:16 psql -h 127.0.0.1 -U assist -d assistdb -f /mnt/init.sql

Após subir, adicione data sources Prometheus (
prometheus
 e Loki (
loki
 e importe dashboards de Node Exporter,










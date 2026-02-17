# 08 -- VM Full Deployment Guide

Author: Armand Amoussou
Project: JAF (Jems Agent Framework)
Reference: branch main, tag v1.4.2, commit 9cbda91

---

## 1. Recommended Operating System

**Primary**: Ubuntu 22.04 LTS (Jammy Jellyfish)
**Alternative**: Ubuntu 24.04 LTS, Debian 12, RHEL 9

Ubuntu 22.04 LTS is recommended for its long-term support (until 2027), stable Python 3.11 availability via deadsnakes PPA, and broad compatibility with all framework dependencies.

---

## 2. Minimum Hardware Configuration

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 2 vCPU | 4 vCPU |
| RAM | 4 GB | 8 GB |
| Storage | 20 GB SSD | 40 GB SSD |
| Network | Internet access (for LLM API calls) | Static IP with DNS |

**Notes**:
- The LLM modes require outbound HTTPS access to OpenAI API endpoints.
- PostgreSQL can run on the same VM for testing or on a separate database server for production.
- Storage requirements increase with process persistence volume and log retention.

---

## 3. System Preparation

### 3.1 Update System

```bash
sudo apt update && sudo apt upgrade -y
```

### 3.2 Install Python 3.11

```bash
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev
```

### 3.3 Install PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
sudo systemctl enable postgresql
sudo systemctl start postgresql
```

### 3.4 Install Git and Build Tools

```bash
sudo apt install -y git build-essential curl
```

---

## 4. Application Installation

### 4.1 Clone Repository

```bash
cd /opt
sudo git clone https://gitlab.com/llm-ai-agents-agentic-ai/multi-agent-framework-entreprise-v2.git jaf
sudo chown -R $USER:$USER /opt/jaf
cd /opt/jaf
```

### 4.2 Create Virtual Environment

```bash
python3.11 -m venv /opt/jaf/venv
source /opt/jaf/venv/bin/activate
```

### 4.3 Install Dependencies

```bash
# Full installation (Core + LLM + API)
pip install --upgrade pip
pip install -r requirements.txt

# Install framework in editable mode
pip install -e .
```

---

## 5. Database Configuration

### 5.1 Create Database User and Database

```bash
sudo -u postgres psql <<EOF
CREATE USER jaf_user WITH PASSWORD 'jaf_secure_password_here';
CREATE DATABASE jaf_prod OWNER jaf_user;
GRANT ALL PRIVILEGES ON DATABASE jaf_prod TO jaf_user;
EOF
```

### 5.2 Apply Migrations

```bash
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/001_create_processes.sql
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/002_create_llm_telemetry.sql
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/003_create_process_events.sql
```

### 5.3 Verify Database

```bash
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod -c "\dt"
```

Expected output: tables `processes`, `llm_telemetry`, `process_events`.

---

## 6. Environment Variables

### 6.1 Create .env File

```bash
cat > /opt/jaf/.env <<'EOF'
# Application
DEBUG=false
LOG_LEVEL=INFO

# API
API_HOST=0.0.0.0
API_PORT=8000

# Database
DATABASE_URL=postgresql+asyncpg://jaf_user:jaf_secure_password_here@localhost:5432/jaf_prod
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10

# LLM
OPENAI_API_KEY=sk-your-production-key-here
DEFAULT_MODEL=gpt-4o-mini
DEFAULT_TEMPERATURE=0.0
LLM_TIMEOUT=60
LLM_MAX_RPM=10

# Engine
DEFAULT_ENGINE=crewai

# Features
ENABLE_PERSISTENCE=true
ENABLE_EVENTS=true
ENABLE_METRICS=false
EOF

chmod 600 /opt/jaf/.env
```

---

## 7. Service Launch

### 7.1 Manual Launch (Testing)

```bash
cd /opt/jaf
source venv/bin/activate
uvicorn jaf.api.main:app --host 0.0.0.0 --port 8000
```

### 7.2 Systemd Service (Production)

```bash
sudo cat > /etc/systemd/system/jaf.service <<'EOF'
[Unit]
Description=JAF Agent Framework API
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=jaf
Group=jaf
WorkingDirectory=/opt/jaf
Environment=PATH=/opt/jaf/venv/bin:/usr/local/bin:/usr/bin
EnvironmentFile=/opt/jaf/.env
ExecStart=/opt/jaf/venv/bin/uvicorn jaf.api.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable jaf
sudo systemctl start jaf
```

---

## 8. Verification

### 8.1 API Health Check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected response:
```json
{
    "status": "ok",
    "framework": "JAF",
    "version": "0.1.0"
}
```

### 8.2 UI Verification

Open `http://<VM_IP>:8000/` in a browser. The SPA should display:
- Navigation bar with JAF logo
- Overview page with execution mode descriptions
- Demos page with 8 available scenarios

### 8.3 API Endpoint Verification

```bash
# List demos
curl -s http://localhost:8000/api/v1/demos | python3 -m json.tool

# List processes
curl -s http://localhost:8000/api/v1/processes | python3 -m json.tool
```

### 8.4 Run a Test Demo

```bash
# Start a demo (returns process_id)
curl -s -X POST http://localhost:8000/api/v1/demos/customer_intelligence/run | python3 -m json.tool

# Stream events (replace PROCESS_ID)
curl -N http://localhost:8000/api/v1/stream/PROCESS_ID
```

---

## 9. Logs

### 9.1 Application Logs

```bash
# If running via systemd
sudo journalctl -u jaf -f

# If running manually
# Logs output to stdout/stderr in JSON format
```

### 9.2 PostgreSQL Logs

```bash
sudo tail -f /var/log/postgresql/postgresql-14-main.log
```

### 9.3 Uvicorn Access Logs

Uvicorn logs HTTP requests to stdout by default. With systemd, these are captured by journald.

---

## 10. Debug Procedures

### 10.1 Check Service Status

```bash
sudo systemctl status jaf
```

### 10.2 Check Database Connectivity

```bash
source /opt/jaf/venv/bin/activate
python3 -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
async def check():
    engine = create_async_engine('postgresql+asyncpg://jaf_user:jaf_secure_password_here@localhost:5432/jaf_prod')
    async with engine.connect() as conn:
        result = await conn.execute(__import__('sqlalchemy').text('SELECT 1'))
        print(f'Database OK: {result.scalar()}')
    await engine.dispose()
asyncio.run(check())
"
```

### 10.3 Check LLM Connectivity

```bash
source /opt/jaf/venv/bin/activate
python3 -c "
import openai, os
from dotenv import load_dotenv
load_dotenv('/opt/jaf/.env')
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
response = client.chat.completions.create(model='gpt-4o-mini', messages=[{'role':'user','content':'ping'}], max_tokens=5)
print(f'LLM OK: {response.choices[0].message.content}')
"
```

### 10.4 Inspect Process State

```bash
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod -c "SELECT id, status, created_at FROM processes ORDER BY created_at DESC LIMIT 10;"
```

---

## 11. Rollback Procedure

### 11.1 Application Rollback

```bash
# Stop service
sudo systemctl stop jaf

# Checkout previous known-good commit
cd /opt/jaf
git log --oneline -5
git checkout <previous_commit_hash>

# Reinstall dependencies
source venv/bin/activate
pip install -r requirements.txt
pip install -e .

# Restart service
sudo systemctl start jaf
```

### 11.2 Database Rollback

The migration files are additive (CREATE TABLE IF NOT EXISTS). To roll back a migration:

```bash
# Drop specific table (use with extreme caution)
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod -c "DROP TABLE IF EXISTS process_events CASCADE;"
```

### 11.3 Full Reset

```bash
sudo systemctl stop jaf
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod -c "DROP TABLE IF EXISTS process_events, llm_telemetry, processes CASCADE; DROP TYPE IF EXISTS process_status, process_event_status CASCADE;"
# Re-apply migrations
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/001_create_processes.sql
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/002_create_llm_telemetry.sql
PGPASSWORD=jaf_secure_password_here psql -U jaf_user -h localhost -d jaf_prod < /opt/jaf/migrations/003_create_process_events.sql
sudo systemctl start jaf
```

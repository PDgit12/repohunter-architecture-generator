# 🏹 RepoHunter: Runtime-Only Architecture Generator

RepoHunter is a lean CLI/API project that uses a local validated repo corpus, RAG retrieval, and **parallel specialist agents** to generate production-ready `architecture.md` blueprints and copy-paste implementation prompts.

Core loop: Retrieval ➔ Parallel Agent Planning ➔ Reviewer Loop ➔ Synthesis ➔ `architecture.md`.

---

## 🏗️ Technical Architecture

### 🛡️ Core Infrastructure
- **Local Control Center**: `repohunter` CLI + `hub.py` minimal runtime launcher.
- **API Service**: `github_repohunter/server.py` for `/chat`, `/architecture/generate`, `/status`.
- **Knowledge Plane**: local validated JSON/JSONL corpus + ChromaDB vector index.

### 🧩 Directory Structure
- `hub.py`: minimal runtime launcher for architecture generation and status.
- `github_repohunter/server.py`: API bridge (`/chat`, `/architecture/generate`, `/status`).
- `github_repohunter/architecture_agents.py`: Parallel agent mesh + markdown renderer.
- `github_repohunter/rag_engine.py`: Chroma index build/retrieval.
- `github_repohunter/database/validated/`: Runtime evidence corpus used by retrieval.

---

## 🚀 OSS Quickstart (Clone → Run)

```bash
git clone <your-repo-url>
cd repohunter-architecture-generator
python3 -m venv venv && source venv/bin/activate
pip install -e .
repohunter demo --output architecture.demo.md
```

If this command succeeds, the project is working end-to-end.

## 🐳 Docker Compose (API + Redis, internet-grade local stack)

```bash
cp .env.docker.example .env
docker compose up --build -d
```

Health check:
```bash
curl http://localhost:8000/status
```

Protected architecture generation:
```bash
curl -X POST http://localhost:8000/architecture/generate \
  -H "Content-Type: application/json" \
  -H "X-Architecture-Key: replace_me_key_v1" \
  -d '{
    "product_name":"Compose Demo Product",
    "requirement":"Need internet-grade multi-agent architecture generation",
    "write_file":true,
    "output_path":"architecture.compose.demo.md"
  }'
```

Stop stack:
```bash
docker compose down
```

## 🧰 CLI Commands

### 1) One-command showcase
```bash
repohunter demo --output architecture.demo.md
```

### 2) Real generation
```bash
repohunter generate \
  --product "Acme AI Copilot" \
  --requirement "Design a scalable multi-agent architecture planner for SaaS engineering teams" \
  --stack FastAPI --stack PostgreSQL --stack Redis \
  --output architecture.md
```

### 3) JSON summary mode
```bash
repohunter generate \
  --product "Acme AI Copilot" \
  --requirement "Need a robust architecture generation system" \
  --json
```

### 4) Local status
```bash
repohunter status
```

## 🔐 Security Defaults

- `ARCHITECTURE_API_KEY` (optional): if set, `/architecture/generate` requires header `X-Architecture-Key`.
- `ARCH_RATE_LIMIT_PER_MIN`: in-memory per-client rate limit for architecture generation endpoint.
- `ALLOW_ORIGINS`: explicit CORS allowlist; no wildcard origin by default.
- `EXPERT_API_KEY`: required on cloud expert server (`/recommend`) for authenticated usage.

Example:
```bash
export ARCHITECTURE_API_KEY="your-strong-key"
export ARCH_RATE_LIMIT_PER_MIN=20
export ALLOW_ORIGINS="http://localhost:5173,http://127.0.0.1:5173"
```

## Getting Started (Detailed)

### 1. Prerequisites
- Python 3.10+
- Docker (optional, for compose mode)

### 2. Local setup
```bash
git clone <your-repo-url>
cd repohunter-architecture-generator
python3 -m venv venv && source venv/bin/activate
pip install -e .
```

### 3. Generate `architecture.md`
Use CLI:
```bash
repohunter generate \
  --product "Your Product" \
  --requirement "Need a scalable multi-agent coding architecture" \
  --output architecture.md
```

Or use API directly:
```bash
curl -X POST http://localhost:8000/architecture/generate \
  -H "Content-Type: application/json" \
  -d '{
    "product_name":"Your Product",
    "requirement":"Need a scalable multi-agent coding architecture",
    "write_file":true,
    "output_path":"architecture.md"
  }'
```

### 4. Optional: Runtime hub launcher
```bash
python hub.py generate
python hub.py status
```

---

## 🤝 Six-Agent Collaboration Model

RepoHunter runs six parallel, communicating agents across three domains:

- Planning domain
  - `planning-scope-agent`
  - `planning-structure-agent`
- Quality/Security domain
  - `quality-code-agent`
  - `security-agent`
- Implementation domain
  - `implementation-writer-agent`
  - `implementation-refactor-agent`

All agents read/write to a shared blackboard so domain outputs feed each other.
The final `architecture.md` includes:
- domain-specific reports
- progress timeline updates
- implementation prompt and evidence

---

## 🛠️ Production Roadmap
- [ ] **Secret Management**: remove hardcoded defaults, use secret manager.
- [ ] **Observability**: request tracing + metrics + dashboard.
- [ ] **Reliability**: typed event contracts for agent mesh and retries/timeouts.
- [ ] **Testing**: API and architecture artifact golden tests.

---

# Adaptive Edge-Cloud Image/Video Processing System v2.0

> Intelligent LOCAL / CLOUD / SPLIT execution for image/video processing with auto-scaling, parallel computing, and real-time benchmarking.

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Docker (for Redis)

### 1. Install Backend Dependencies
```bash
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies
```bash
cd frontend && npm install && cd ..
```

### 3. Configure Environment
```bash
copy .env.example .env
# Edit .env if needed (defaults work for development)
```

### 4. Launch Everything
```bash
run.bat
```

Or manually:
```bash
# Terminal 1: Redis
docker-compose up -d

# Terminal 2: Celery Worker
python -m celery -A orchestrator.tasks worker --loglevel=info --pool=solo

# Terminal 3: Backend
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 4: Frontend
cd frontend && npm start
```

### 5. Open Dashboard
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

## Architecture

```
User → Frontend → Backend API → Orchestrator → Decision Engine
  → Processing (LOCAL / CLOUD / SPLIT) → Benchmark → UI
```

## Modules

| Module | Directory | Stack |
|--------|-----------|-------|
| Frontend | `frontend/` | React + Chart.js |
| Backend | `backend/` | FastAPI |
| Agent | `agent/` | psutil, GPUtil |
| Decision | `decision/` | Python |
| Orchestrator | `orchestrator/` | Celery + Redis |
| Processing | `processing/` | multiprocessing, PyTorch, Ray |
| Cloud | `cloud/` | boto3 / Simulator |
| Benchmark | `benchmark/` | psutil |
| ML (RL) | `ml/` | PyTorch DQN |
| Storage | `storage/` | Filesystem + S3 |
| Observability | `observability/` | Structured JSON |

## Default Credentials (Dev Mode)
- Username: `admin` / Password: `admin123`
- Auth is disabled by default (`AUTH_ENABLED=false`)

## Train RL Agent (Optional)
```bash
python -m ml.trainer --episodes 1000
```

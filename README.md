# AI Video Automation SaaS

Production-ready AI video automation platform built with FastAPI, Celery, Ollama (Llama 3), Whisper, Piper TTS, and FFmpeg.

---

## Architecture

```
┌─────────────┐    ┌──────────────────────────────────────────┐
│   Flutter   │───▶│  Nginx  →  FastAPI (uvicorn)             │
│   Frontend  │    │           ↓          ↓                   │
└─────────────┘    │  PostgreSQL    Redis (broker+cache)       │
                   │           ↓                              │
                   │  Celery Workers                          │
                   │    ├── Whisper (transcription)           │
                   │    ├── Ollama / Llama 3 (script gen)     │
                   │    ├── Piper TTS (voice synthesis)       │
                   │    └── FFmpeg (video merge)              │
                   └──────────────────────────────────────────┘
```

**Clean Architecture layers:**
- `app/core/` — config, security, exceptions, logging
- `app/domain/` — entities, repository interfaces, domain services
- `app/infrastructure/` — SQLAlchemy repos, Celery tasks, AI clients
- `app/api/` — FastAPI endpoints, Pydantic schemas, dependencies

---

## Quick Start

### 1. Prerequisites
- Docker 24+ and Docker Compose v2
- 8 GB RAM minimum (16 GB recommended for Llama 3)
- 20 GB free disk space (Llama 3 model ~4.7 GB)

### 2. Clone and configure

```bash
git clone <repo-url>
cd ai-video-saas
cp .env.example .env
```

Edit `.env` — at minimum change:
```
APP_SECRET_KEY=<openssl rand -hex 32>
JWT_SECRET_KEY=<openssl rand -hex 64>
POSTGRES_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
FIRST_SUPERUSER_PASSWORD=<admin-password>
```

### 3. Start all services

```bash
# Development (with hot-reload)
docker compose up -d

# Check all services are healthy
docker compose ps

# Follow logs
docker compose logs -f api celery_worker
```

### 4. Run database migrations

```bash
docker compose run --rm migrate
```

### 5. Pull the Llama 3 model (runs automatically, but can be triggered manually)

```bash
docker compose run --rm ollama_pull
```

### 6. Verify the API

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"0.1.0","env":"development","db":"ok"}

curl http://localhost:8000/docs   # Swagger UI
```

---

## API Reference

### Authentication

All protected endpoints require: `Authorization: Bearer <access_token>`

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login → access + refresh tokens |
| POST | `/api/v1/auth/refresh` | Exchange refresh → new token pair |
| POST | `/api/v1/auth/logout` | Invalidate all sessions |
| GET | `/api/v1/auth/me` | Current user profile |

**Login example:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@aivideosaas.com","password":"<your-password>"}'
```

### Users

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/v1/users/` | No | Register new account |
| GET | `/api/v1/users/me` | Yes | Get own profile |
| PATCH | `/api/v1/users/me` | Yes | Update profile |
| POST | `/api/v1/users/me/password` | Yes | Change password |
| GET | `/api/v1/users/` | Admin | List all users |
| GET | `/api/v1/users/{id}` | Admin | Get user by ID |

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/projects/` | Create project |
| GET | `/api/v1/projects/` | List own projects |
| GET | `/api/v1/projects/{id}` | Get project |
| PATCH | `/api/v1/projects/{id}` | Update project |
| DELETE | `/api/v1/projects/{id}` | Delete project |

### Videos

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/videos/projects/{project_id}/videos` | Create video record |
| POST | `/api/v1/videos/{id}/upload` | Upload source file (multipart) |
| POST | `/api/v1/videos/{id}/process` | Enqueue AI pipeline (→ 202) |
| GET | `/api/v1/videos/{id}/status` | Poll processing status |
| GET | `/api/v1/videos/projects/{project_id}/videos` | List project videos |
| GET | `/api/v1/videos/{id}?project_id=...` | Get video |
| DELETE | `/api/v1/videos/{id}?project_id=...` | Delete video |

**Full upload + process flow:**
```bash
TOKEN="<access_token>"
PROJECT_ID="<project-uuid>"

# 1. Create video record
VIDEO=$(curl -s -X POST http://localhost:8000/api/v1/videos/projects/$PROJECT_ID/videos \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"My AI Video","script_prompt":"Make it engaging"}')
VIDEO_ID=$(echo $VIDEO | jq -r .id)

# 2. Upload source file
curl -X POST http://localhost:8000/api/v1/videos/$VIDEO_ID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@/path/to/video.mp4"

# 3. Trigger processing
TASK=$(curl -s -X POST http://localhost:8000/api/v1/videos/$VIDEO_ID/process \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}')
TASK_ID=$(echo $TASK | jq -r .task_id)

# 4. Poll status
curl http://localhost:8000/api/v1/tasks/$TASK_ID/status \
  -H "Authorization: Bearer $TOKEN"
```

### Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/tasks/{id}` | Full task detail + logs |
| GET | `/api/v1/tasks/{id}/status` | Lightweight poll (progress 0–100%) |
| GET | `/api/v1/tasks/video/{video_id}` | All tasks for a video |

---

## Testing

```bash
# Run all tests
docker compose run --rm api pytest

# Unit tests only (fast, no DB)
docker compose run --rm api pytest -m unit

# Integration tests only (requires running DB)
docker compose run --rm api pytest -m integration

# With coverage report
docker compose run --rm api pytest --cov=app --cov-report=html

# Specific file
docker compose run --rm api pytest tests/unit/test_auth_service.py -v
```

---

## Piper Voice Models

Download models from https://huggingface.co/rhasspy/piper-voices and place both `.onnx` and `.onnx.json` files in `./backend/models/piper/`:

```bash
mkdir -p backend/models/piper
cd backend/models/piper

# Example: download en_US-lessac-medium
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json
```

---

## Production Deployment

```bash
# Build production images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start with production config
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale workers
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
  up -d --scale celery_worker=4
```

---

## Environment Variables

See `.env.example` for full documentation of all 80+ configuration variables.

Key groups:
- `APP_*` — application identity and debug flags
- `JWT_*` — token expiry and signing key
- `POSTGRES_*` / `DB_*` — database and connection pool
- `REDIS_*` — Redis connection and DB selection
- `CELERY_*` — task queue behavior
- `OLLAMA_*` — Llama 3 inference settings
- `WHISPER_*` — transcription model and device
- `PIPER_*` — TTS binary and model paths
- `FFMPEG_*` — video codec and quality settings
- `STORAGE_*` — local or S3 file storage

---

## Monitoring

| Service | URL | Credentials |
|---------|-----|-------------|
| API Swagger | http://localhost:8000/docs | — |
| Flower (Celery) | http://localhost:5555 | `FLOWER_USER` / `FLOWER_PASSWORD` |
| PostgreSQL | localhost:5432 | `POSTGRES_USER` / `POSTGRES_PASSWORD` |
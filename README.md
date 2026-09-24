# Elicius AI Question-Answering API

A small production-shaped FastAPI service that takes a user's question,
authenticates them with JWT, sends the question to an LLM (Gemini,
with automatic fallback to Groq), and returns the answer — with
caching, rate limiting, retries, and Prometheus metrics along the way.

Built for the Elicius Energy AI/LLM Platform & DevOps Engineer take-home
assessment.

## What's inside

| Requirement | Where |
|---|---|
| `POST /auth/login` | `app/main.py` + `app/auth.py` |
| `POST /chat` (auth, LLM call, retry/fallback, latency, tokens, errors) | `app/main.py` + `app/llm_client.py` |
| `GET /health` | `app/main.py` |
| `GET /metrics` (Prometheus) | `app/main.py` + `app/metrics.py` |
| JWT auth + RBAC | `app/auth.py`, design notes in `AUTH_DESIGN.md` |
| Docker / Compose | `Dockerfile`, `docker-compose.yml` |
| Environment-based config, no hard-coded secrets | `app/config.py`, `.env.example` |
| Scaling to 500 req/s + EC2→10k-user migration | `ARCHITECTURE.md` |
| Tests | `tests/` (14 tests — auth, RBAC, caching, retry/fallback, rate limit, health, metrics) |

## Quick start (Docker — recommended)

1. Copy the example env file and fill in your real values:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and set `JWT_SECRET_KEY` (any long random string) and
   at least `GEMINI_API_KEY` (get one free at aistudio.google.com) —
   `GROQ_API_KEY` (console.groq.com) is optional but enables the
   fallback path.

2. Start everything:
   ```bash
   docker compose up --build
   ```
   This builds the API image and starts the API, Redis, and
   PostgreSQL containers together.

3. The API is now at `http://localhost:8000`. Interactive docs
   (Swagger UI) are at `http://localhost:8000/docs`.

## Quick start (without Docker, for local development)

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start Redis locally (or point `REDIS_URL` in `.env` at any running
   Redis instance).
3. By default `DATABASE_URL` falls back to a local SQLite file, so
   PostgreSQL isn't required just to try the app out.
4. Run the server:
   ```bash
   uvicorn app.main:app --reload
   ```

## Demo accounts

Three users are seeded automatically the first time the app starts,
one per role (see `AUTH_DESIGN.md` for what each role can do):

| Username | Password | Role |
|---|---|---|
| `admin` | `admin123` | admin |
| `alice` | `alice123` | user |
| `viewer` | `viewer123` | readonly |

## Trying it out

```bash
# 1. Log in and grab a token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "alice", "password": "alice123"}'

# 2. Ask a question (paste the access_token from step 1)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN>" \
  -d '{"question": "What is FastAPI?"}'

# 3. Check health
curl http://localhost:8000/health

# 4. Check metrics
curl http://localhost:8000/metrics
```

## Running the tests

```bash
pip install -r requirements.txt
pytest tests/ -v
```

Tests use an in-memory SQLite database and `fakeredis`, and mock the
LLM calls directly — so the full suite runs in under a second with no
real API keys, no Docker, and no network access required. All 14 pass.

## Notes on design decisions

Full reasoning for the architecture, scaling plan, and SSO/RBAC design
lives in `ARCHITECTURE.md` and `AUTH_DESIGN.md` rather than crammed
into this README, since the assignment explicitly asks for that
reasoning to be explained, not just implemented.

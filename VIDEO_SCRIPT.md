# 5-minute video talking points

Don't read this word for word — say it in your own words, on camera or
voice-over, screen-sharing the repo/terminal as you go. Roughly 40-50
seconds per section keeps you at 5 minutes.

**1. What it does (30-40s)**
"This is a Question-Answering API. A user logs in, gets a JWT, asks a
question, and the API sends it to Gemini — or Groq if Gemini is down —
and returns the answer, while logging latency and token usage."

**2. Auth + RBAC (45s)** — show `/docs`, log in as `alice`, then as
`viewer`.
"JWT auth: login returns a signed token with the user's role baked in.
Three roles — admin, user, readonly. Watch: `viewer` gets a 403 on
/chat because read-only accounts can't trigger paid LLM calls, only
admin and user can."

**3. The /chat flow (60s)** — run a real question, then run it again.
"First call: rate limit check, cache miss, calls Gemini, logs latency
and tokens, caches the answer. Second identical call: instant, from
cache — you can see `provider: cache` in the response."

**4. Retry / fallback / error handling (45s)** — mention or show the
503 test.
"If Gemini fails, it retries twice with exponential backoff, then
falls back to Groq. If both are down, it returns a clean 503, not a
crash — I tested this exact path with both keys blank and it works."

**5. Docker + Redis + Postgres (30s)** — show `docker-compose.yml`.
"One `docker compose up` starts the API, Redis, and Postgres together.
No secrets in the code — everything comes from environment variables."

**6. Metrics + tests (30s)** — show `/metrics` and `pytest` output.
"Prometheus metrics for request count, latency, and tokens. 14 tests
covering auth, RBAC, caching, retries, and rate limiting — all
passing, no real API keys needed since the LLM calls are mocked."

**7. Scaling answer (20-30s)**
"For 500 req/s I'd run multiple FastAPI instances behind a load
balancer with Kubernetes HPA, Redis for shared caching and rate
limiting, and the same retry/fallback chain protecting against LLM
provider limits — it's all diagrammed in ARCHITECTURE.md."

**Close (10s):** "Repo link and README are in the submission — thanks
for reviewing."

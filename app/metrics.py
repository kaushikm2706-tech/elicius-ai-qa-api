"""
Prometheus is the industry-standard tool for the /metrics endpoint the
assignment asks for. Plain-English picture: it's a shared notebook —
every request scribbles a line ("took 340ms", "used 120 tokens"), and
a monitoring dashboard (Grafana, in production) reads the whole
notebook periodically to draw graphs.

Three notebooks (metrics) are kept:
  - CHAT_REQUESTS: a running count, split by whether it succeeded,
    errored, or was blocked by the rate limiter.
  - CHAT_LATENCY: a histogram (a "how long did requests take" bucket
    count) of /chat call durations — this is the "record request
    latency" requirement.
  - TOKENS_USED: a running count of tokens spent, split by prompt vs.
    completion — this is the "record LLM token usage" requirement.
"""
from prometheus_client import Counter, Histogram

CHAT_REQUESTS = Counter(
    "chat_requests_total",
    "Total number of /chat requests",
    ["status"],  # success | error | rate_limited
)

CHAT_LATENCY = Histogram(
    "chat_request_latency_seconds",
    "Latency of /chat requests in seconds",
)

TOKENS_USED = Counter(
    "llm_tokens_total",
    "Total LLM tokens consumed",
    ["token_type"],  # prompt | completion
)

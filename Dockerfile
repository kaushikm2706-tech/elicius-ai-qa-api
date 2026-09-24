# --- Base image ---
# slim = the regular Python image with unneeded extras stripped out,
# so the final container is smaller and has a smaller attack surface.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies FIRST, before copying the rest of the code.
# Docker caches each step: if only your .py files change later, Docker
# reuses this dependency layer instead of reinstalling everything —
# much faster rebuilds during development.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Now copy the actual application code.
COPY app ./app

# Document which port the app listens on (informational; doesn't
# actually publish the port — that happens in docker-compose.yml or
# `docker run -p`).
EXPOSE 8000

# Basic container-level health check so `docker ps` and orchestrators
# can see if the app is actually responding, not just "running".
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

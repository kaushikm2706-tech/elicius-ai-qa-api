"""
Shared test setup. Two things are swapped out for testing so tests
never touch a real database, real Redis, or the real internet:
  - DATABASE_URL -> an in-memory SQLite DB (fresh for every test run)
  - the Redis client -> fakeredis (an in-memory look-alike)
LLM calls are mocked per-test with monkeypatch instead of being global,
since different tests need different fake LLM behaviour (success,
timeout, both providers down, etc).
"""
import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/0"

import fakeredis
import pytest
from fastapi.testclient import TestClient

from app import cache as cache_module
from app.database import Base, engine
from app.main import app

# Swap the real Redis connection for an in-memory fake one.
cache_module.redis_client = fakeredis.FakeStrictRedis(decode_responses=True)


@pytest.fixture(autouse=True)
def _fresh_database_and_cache():
    # Runs before EVERY test: fresh DB tables and a wiped fake-Redis,
    # so no test's cache entries or rate-limit counters leak into the
    # next one. Without this, test order could silently change results.
    Base.metadata.create_all(bind=engine)
    cache_module.redis_client.flushall()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_token(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    return resp.json()["access_token"]


@pytest.fixture
def user_token(client):
    resp = client.post("/auth/login", json={"username": "alice", "password": "alice123"})
    return resp.json()["access_token"]


@pytest.fixture
def readonly_token(client):
    resp = client.post("/auth/login", json={"username": "viewer", "password": "viewer123"})
    return resp.json()["access_token"]

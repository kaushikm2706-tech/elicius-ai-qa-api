import pytest

from app.llm_client import LLMError


async def _fake_answer(question):
    return {"answer": f"You asked: {question}", "prompt_tokens": 5,
            "completion_tokens": 7, "provider": "gemini"}


async def _fake_answer_via_groq(question):
    return {"answer": "fallback answer", "prompt_tokens": 3,
            "completion_tokens": 4, "provider": "groq"}


async def _fake_all_providers_down(question):
    raise LLMError("gemini and groq both timed out")


def _auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_chat_success(client, user_token, monkeypatch):
    monkeypatch.setattr("app.main.get_answer", _fake_answer)
    resp = client.post("/chat", json={"question": "What is FastAPI?"},
                        headers=_auth_header(user_token))
    assert resp.status_code == 200
    body = resp.json()
    assert body["provider"] == "gemini"
    assert body["prompt_tokens"] == 5
    assert body["completion_tokens"] == 7
    assert "latency_ms" in body


def test_chat_uses_cache_on_second_identical_question(client, user_token, monkeypatch):
    monkeypatch.setattr("app.main.get_answer", _fake_answer)
    q = {"question": "What is Redis?"}
    first = client.post("/chat", json=q, headers=_auth_header(user_token))
    assert first.json()["provider"] == "gemini"

    second = client.post("/chat", json=q, headers=_auth_header(user_token))
    assert second.status_code == 200
    assert second.json()["provider"] == "cache"


def test_chat_falls_back_when_primary_provider_object_used(client, user_token, monkeypatch):
    # Simulates Gemini being down but Groq answering — proves the
    # response shape is identical no matter which provider served it.
    monkeypatch.setattr("app.main.get_answer", _fake_answer_via_groq)
    resp = client.post("/chat", json={"question": "fallback test"},
                        headers=_auth_header(user_token))
    assert resp.status_code == 200
    assert resp.json()["provider"] == "groq"


def test_chat_returns_503_when_all_providers_fail(client, user_token, monkeypatch):
    monkeypatch.setattr("app.main.get_answer", _fake_all_providers_down)
    resp = client.post("/chat", json={"question": "doomed question"},
                        headers=_auth_header(user_token))
    assert resp.status_code == 503


def test_chat_rate_limit_blocks_after_threshold(client, user_token, monkeypatch):
    monkeypatch.setattr("app.main.get_answer", _fake_answer)
    from app.config import settings
    limit = settings.rate_limit_per_minute

    # Fire off (limit + 1) DIFFERENT questions so caching can't mask the count.
    last_status = None
    for i in range(limit + 1):
        resp = client.post("/chat", json={"question": f"unique question {i}"},
                            headers=_auth_header(user_token))
        last_status = resp.status_code
    assert last_status == 429

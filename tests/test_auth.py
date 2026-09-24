def test_login_succeeds_with_correct_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "admin123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "admin"
    assert body["token_type"] == "bearer"
    assert len(body["access_token"]) > 20


def test_login_fails_with_wrong_password(client):
    resp = client.post("/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_login_fails_for_unknown_user(client):
    resp = client.post("/auth/login", json={"username": "ghost", "password": "x"})
    assert resp.status_code == 401


def test_chat_without_token_is_rejected(client):
    resp = client.post("/chat", json={"question": "hello"})
    assert resp.status_code == 401


def test_readonly_role_cannot_use_chat(client, readonly_token):
    resp = client.post(
        "/chat",
        json={"question": "hello"},
        headers={"Authorization": f"Bearer {readonly_token}"},
    )
    assert resp.status_code == 403


def test_readonly_cannot_access_admin_stats(client, readonly_token):
    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {readonly_token}"})
    assert resp.status_code == 403


def test_admin_can_access_admin_stats(client, admin_token):
    resp = client.get("/admin/stats", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp.status_code == 200
    assert "total_chat_requests" in resp.json()

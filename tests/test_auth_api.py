from fastapi.testclient import TestClient

from app.main import app


def test_auth_token_success(monkeypatch):
    def _ok_user(username: str, password: str) -> bool:
        return username == "admin" and password == "secret"

    monkeypatch.setattr("app.services.auth.authenticate_user", _ok_user)
    client = TestClient(app)

    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "secret"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["token_type"] == "bearer"
    assert "access_token" in payload
    assert payload["expires_in"] > 0


def test_auth_token_invalid(monkeypatch):
    def _deny_user(username: str, password: str) -> bool:
        return False

    monkeypatch.setattr("app.services.auth.authenticate_user", _deny_user)
    client = TestClient(app)

    response = client.post(
        "/auth/token",
        data={"username": "admin", "password": "bad"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"

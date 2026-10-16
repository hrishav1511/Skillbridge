from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from jose import jwt

from skillbridge.api.repositories.auth.config import auth_config
from skillbridge.api.repositories.auth import token as token_module
from skillbridge.api.repositories.auth.token import validate_token


app = FastAPI()


@app.get("/protected")
@validate_token
async def protected(request: Request, user_id: UUID | None = None):
    return {"user_id": str(user_id), "is_uuid": isinstance(user_id, UUID)}


def _active_user_session(expected_user_id):
    class Session:
        async def get(self, _model, user_id):
            if user_id == expected_user_id:
                return SimpleNamespace(id=user_id, status="ACTIVE")
            return None

    @asynccontextmanager
    async def get_session():
        yield Session()

    return get_session


def _token(user_id, token_type="access"):
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": int((datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp()),
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "type": token_type,
            "jti": str(uuid4()),
        },
        auth_config.JWT_SECRET_KEY,
        algorithm=auth_config.JWT_ALGORITHM,
    )


def test_validate_token_injects_uuid_user_id(monkeypatch):
    expected_user_id = uuid4()
    monkeypatch.setattr(token_module, "get_session", _active_user_session(expected_user_id))
    token = _token(expected_user_id)

    with TestClient(app) as client:
        response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200, response.text
    assert response.json()["user_id"] == str(expected_user_id)
    assert UUID(response.json()["user_id"]) == expected_user_id
    assert response.json()["is_uuid"] is True


def test_validate_token_rejects_refresh_token(monkeypatch):
    expected_user_id = uuid4()
    monkeypatch.setattr(token_module, "get_session", _active_user_session(expected_user_id))

    with TestClient(app) as client:
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {_token(expected_user_id, 'refresh')}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "An access token is required."


def test_validate_token_rejects_deleted_user(monkeypatch):
    existing_user_id = uuid4()
    monkeypatch.setattr(token_module, "get_session", _active_user_session(existing_user_id))

    with TestClient(app) as client:
        response = client.get(
            "/protected",
            headers={"Authorization": f"Bearer {_token(uuid4())}"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "User account no longer exists."

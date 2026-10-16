from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from jose import jwt
from starlette.websockets import WebSocketDisconnect

from skillbridge.api.api_v1.endpoints import ws as ws_endpoint
from skillbridge.api.repositories.auth.config import auth_config


app = FastAPI()
app.include_router(ws_endpoint.router)


def _token(user_id, token_type="access"):
    now = datetime.now(timezone.utc)
    return jwt.encode(
        {
            "sub": str(user_id),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "iat": int(now.timestamp()),
            "type": token_type,
            "jti": str(uuid4()),
        },
        auth_config.JWT_SECRET_KEY,
        algorithm=auth_config.JWT_ALGORITHM,
    )


@pytest.mark.parametrize("query", ["", "?token=not-a-jwt"])
def test_websocket_rejects_missing_or_invalid_token(query):
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{uuid4()}{query}"):
                pass

    assert exc.value.code == 4401


def test_websocket_rejects_url_identity_mismatch():
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{uuid4()}?token={_token(uuid4())}"):
                pass

    assert exc.value.code == 4401


def test_websocket_rejects_refresh_token():
    user_id = uuid4()
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc:
            with client.websocket_connect(f"/ws/{user_id}?token={_token(user_id, 'refresh')}"):
                pass

    assert exc.value.code == 4401


def test_websocket_accepts_active_matching_user(monkeypatch):
    user_id = uuid4()

    class Session:
        async def get(self, _model, requested_user_id):
            return SimpleNamespace(id=requested_user_id, status="ACTIVE")

    @asynccontextmanager
    async def fake_session():
        yield Session()

    monkeypatch.setattr(ws_endpoint, "get_session", fake_session)
    with TestClient(app) as client:
        with client.websocket_connect(f"/ws/{user_id}?token={_token(user_id)}") as websocket:
            websocket.close()

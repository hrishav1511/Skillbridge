from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from skillbridge.api.api_v1.endpoints import role as role_endpoint
from skillbridge.api.repositories.auth import register as register_module
from skillbridge.api.repositories.auth.register import RegisterRepository
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.exceptions import CannotRegisterError


app = FastAPI()
app.include_router(role_endpoint.router)


def test_unauthenticated_role_creation_is_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/create/",
            json={"title": "ADMIN", "slug": "admin", "description": "Administrator"},
        )

    assert response.status_code == 401


def test_public_role_listing_hides_privileged_roles(monkeypatch):
    roles = [
        SimpleNamespace(slug="student", to_dict=lambda: {"slug": "student"}),
        SimpleNamespace(slug="tutor", to_dict=lambda: {"slug": "tutor"}),
        SimpleNamespace(slug="admin", to_dict=lambda: {"slug": "admin"}),
    ]

    async def fake_results(self, query):
        return {"success": True, "message": "ok", "metadata": {"total": 3}, "data": roles}

    monkeypatch.setattr(role_endpoint.RoleRepository, "get_paginated_results", fake_results)
    with TestClient(app) as client:
        response = client.get("/roles/")

    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["data"]] == ["student", "tutor"]
    assert response.json()["metadata"]["total"] == 2


@pytest.mark.asyncio
async def test_public_registration_rejects_admin_role(monkeypatch):
    @asynccontextmanager
    async def fake_session():
        yield SimpleNamespace()

    async def fake_role_get(self, _id, session):
        return {"data": SimpleNamespace(slug="admin")}

    monkeypatch.setattr(register_module, "get_session", fake_session)
    monkeypatch.setattr(register_module.RoleRepository, "get", fake_role_get)
    payload = UserRegisterInputValidator(
        full_name="Not Admin",
        email="student@hs-fulda.de",
        password="Secure123!",
        confirm_password="Secure123!",
        role_id=uuid4(),
    )

    with pytest.raises(CannotRegisterError, match="student and tutor"):
        await RegisterRepository().register(payload)

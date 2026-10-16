import pytest

from skillbridge.api.services import moderation_service


@pytest.mark.asyncio
async def test_moderation_is_skipped_when_disabled(monkeypatch):
    monkeypatch.setattr(moderation_service.settings, "OPENAI_MODERATION_ENABLED", False)

    result = await moderation_service.moderate_service_content(
        service_name="Python tutoring",
        description="Learn Python",
        tags=["python"],
    )

    assert result.status == "SKIPPED"
    assert result.flagged is False


@pytest.mark.asyncio
async def test_tutor_moderation_skips_when_disabled(monkeypatch):
    monkeypatch.setattr(moderation_service.settings, "OPENAI_MODERATION_ENABLED", False)

    result = await moderation_service.moderate_tutor_content(
        academic_program="Computer Science",
        bio="I teach programming fundamentals and problem solving.",
        tags=["python", "algorithms"],
    )

    assert result.status == "SKIPPED"
    assert result.flagged is False


@pytest.mark.asyncio
async def test_detoxify_flagged_response_is_mapped(monkeypatch):
    monkeypatch.setattr(moderation_service.settings, "OPENAI_MODERATION_ENABLED", True)

    def fake_predict_sync(text):
        assert "Service name: Python tutoring" in text
        return {
            "toxicity": 0.98,
            "severe_toxicity": 0.1,
            "obscene": 0.1,
            "threat": 0.1,
            "insult": 0.2,
            "identity_attack": 0.1,
            "sexual_explicit": 0.1,
        }

    monkeypatch.setattr(moderation_service, "_predict_sync", fake_predict_sync)

    result = await moderation_service.moderate_service_content(
        service_name="Python tutoring",
        description="Learn Python",
        tags=["python"],
    )

    assert result.status == "FLAGGED"
    assert result.flagged is True
    assert result.categories["toxicity"] is True
    assert result.reason == "toxicity"


@pytest.mark.asyncio
async def test_detoxify_error_is_sanitized(monkeypatch):
    monkeypatch.setattr(moderation_service.settings, "OPENAI_MODERATION_ENABLED", True)

    def fake_predict_sync(_text):
        raise ValueError("detoxify model failed")

    monkeypatch.setattr(moderation_service, "_predict_sync", fake_predict_sync)

    result = await moderation_service.moderate_service_content(
        service_name="Python tutoring",
        description="Learn Python",
        tags=["python"],
    )

    assert result.status == "ERROR"
    assert result.flagged is True
    assert result.provider == "detoxify"
    assert result.reason == "Moderation could not be completed at this time."
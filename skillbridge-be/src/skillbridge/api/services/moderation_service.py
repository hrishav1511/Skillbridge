import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from skillbridge.config import settings

logger = logging.getLogger(__name__)


def preload_model() -> None:
    """Force the Detoxify model to load. Call this at app startup."""
    _model()


@dataclass
class ModerationResult:
    status: str
    flagged: bool = False
    categories: dict[str, Any] | None = None
    scores: dict[str, Any] | None = None
    reason: str | None = None
    provider: str | None = None
    moderated_at: datetime | None = None


_THRESHOLDS: dict[str, float] = {
    "toxicity": 0.7,
    "severe_toxicity": 0.5,
    "obscene": 0.7,
    "threat": 0.5,
    "insult": 0.7,
    "identity_attack": 0.5,
    "sexual_explicit": 0.7,
}


@lru_cache(maxsize=1)
def _model():
    from detoxify import Detoxify

    logger.info("Loading Detoxify model (first call only)...")
    return Detoxify("multilingual")


def _content_to_moderate(
    service_name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    academic_program: str | None = None,
    bio: str | None = None,
) -> str:
    parts: list[str] = []
    if service_name:
        parts.append(f"Service name: {service_name}")
    if description:
        parts.append(f"Description: {description}")
    if academic_program:
        parts.append(f"Academic program: {academic_program}")
    if bio:
        parts.append(f"Bio: {bio}")
    if tags:
        parts.append(f"Tags: {', '.join(tags)}")
    return "\n".join(parts).strip()


def _tutor_content_to_moderate(
    academic_program: str | None = None,
    bio: str | None = None,
    tags: list[str] | None = None,
) -> str:
    return _content_to_moderate(
        academic_program=academic_program,
        bio=bio,
        tags=tags,
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _predict_sync(text: str) -> dict[str, float]:
    raw = _model().predict(text)
    return {category: float(score) for category, score in raw.items()}


async def _moderate_text_content(content: str) -> ModerationResult:
    if not settings.OPENAI_MODERATION_ENABLED:
        return ModerationResult(status="SKIPPED")
    if not content:
        return ModerationResult(status="SKIPPED")

    try:
        scores = await asyncio.to_thread(_predict_sync, content)
    except Exception as exc:
        logger.exception("Detoxify moderation failed: %s", exc)
        return ModerationResult(
            status="ERROR",
            flagged=True,
            reason="Moderation could not be completed at this time.",
            provider="detoxify",
            moderated_at=_now(),
        )

    categories = {
        category: scores[category] >= threshold
        for category, threshold in _THRESHOLDS.items()
    }
    flagged = any(categories.values())
    reason = ", ".join(name for name, hit in categories.items() if hit) if flagged else None

    return ModerationResult(
        status="FLAGGED" if flagged else "CLEAR",
        flagged=flagged,
        categories=categories,
        scores=scores,
        reason=reason,
        provider="detoxify",
        moderated_at=_now(),
    )


async def moderate_service_content(
    service_name: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
    academic_program: str | None = None,
    bio: str | None = None,
) -> ModerationResult:
    """Moderate service text locally with Detoxify."""
    content = _content_to_moderate(
        service_name=service_name,
        description=description,
        tags=tags,
        academic_program=academic_program,
        bio=bio,
    )
    return await _moderate_text_content(content)


async def moderate_tutor_content(
    academic_program: str | None = None,
    bio: str | None = None,
    tags: list[str] | None = None,
) -> ModerationResult:
    """Moderate tutor profile content locally with Detoxify."""
    content = _tutor_content_to_moderate(
        academic_program=academic_program,
        bio=bio,
        tags=tags,
    )
    return await _moderate_text_content(content)

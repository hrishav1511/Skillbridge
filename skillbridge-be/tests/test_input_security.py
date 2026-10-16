from io import BytesIO

import pytest
from fastapi import HTTPException, UploadFile
from pydantic import ValidationError
from starlette.datastructures import Headers

from skillbridge.api.schemas.tutor import TutorQueryCriteria
from skillbridge.api.services.media_service import MediaService


def _upload(filename: str, content_type: str, content: bytes) -> UploadFile:
    return UploadFile(
        file=BytesIO(content),
        filename=filename,
        headers=Headers({"content-type": content_type}),
    )


def test_search_rejects_invalid_punctuation_instead_of_sanitizing_it():
    with pytest.raises(ValidationError):
        TutorQueryCriteria(query="Python!!!")


def test_search_rejects_more_than_40_characters():
    with pytest.raises(ValidationError):
        TutorQueryCriteria(query="a" * 41)


@pytest.mark.asyncio
async def test_image_validation_accepts_matching_png_signature():
    content = b"\x89PNG\r\n\x1a\n" + b"valid-image-data"

    assert await MediaService().validate_image(_upload("avatar.png", "image/png", content)) == content


@pytest.mark.asyncio
async def test_image_validation_rejects_spoofed_content():
    with pytest.raises(HTTPException, match="does not match"):
        await MediaService().validate_image(
            _upload("avatar.png", "image/png", b"this is not a png")
        )


@pytest.mark.asyncio
async def test_attachment_validation_rejects_spoofed_pdf():
    with pytest.raises(HTTPException, match="does not match"):
        await MediaService().validate_service_attachment(
            _upload("notes.pdf", "application/pdf", b"plain text")
        )

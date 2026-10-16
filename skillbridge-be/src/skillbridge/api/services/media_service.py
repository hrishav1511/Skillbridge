import asyncio
from pathlib import Path
from uuid import UUID

from fastapi import UploadFile, HTTPException
from typing import Optional
from loguru import logger
from skillbridge.api.core.s3_client import s3_client
from skillbridge.api.repositories.student import StudentRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.database.db.database import get_session


class MediaService:
    # Upload ceilings, in one place so the endpoints, the validators and the
    # error messages cannot drift apart. The Angular forms mirror these for
    # immediate feedback; these are the ones that actually decide.
    SERVICE_IMAGE_MAX_MB = 5
    SERVICE_VIDEO_MAX_MB = 100
    SERVICE_ATTACHMENT_MAX_MB = 50
    PROFILE_PICTURE_MAX_MB = 5
    COVER_PICTURE_MAX_MB = 10

    MAX_SERVICE_IMAGES = 8
    MAX_SERVICE_VIDEOS = 3
    MAX_SERVICE_ATTACHMENTS = 5

    READ_TIMEOUT_SECONDS = 20
    READ_CHUNK_SIZE = 1024 * 1024

    @staticmethod
    def _extension(file: UploadFile) -> str:
        return Path(file.filename or "").suffix.lower()

    @classmethod
    def _validate_image_signature(cls, file: UploadFile, content: bytes) -> None:
        signatures = {
            "image/jpeg": (content.startswith(b"\xff\xd8\xff"), {".jpg", ".jpeg"}),
            "image/jpg": (content.startswith(b"\xff\xd8\xff"), {".jpg", ".jpeg"}),
            "image/png": (content.startswith(b"\x89PNG\r\n\x1a\n"), {".png"}),
            "image/webp": (
                content.startswith(b"RIFF") and content[8:12] == b"WEBP",
                {".webp"},
            ),
        }
        valid_signature, extensions = signatures[file.content_type]
        if not valid_signature or cls._extension(file) not in extensions:
            raise HTTPException(status_code=400, detail="File content does not match its image type or extension.")

    @classmethod
    def _validate_video_signature(cls, file: UploadFile, content: bytes) -> None:
        extension = cls._extension(file)
        if file.content_type == "video/webm":
            valid = content.startswith(b"\x1a\x45\xdf\xa3") and extension == ".webm"
        elif file.content_type == "video/quicktime":
            valid = len(content) >= 12 and content[4:8] == b"ftyp" and extension == ".mov"
        else:
            valid = len(content) >= 12 and content[4:8] == b"ftyp" and extension in {".mp4", ".m4v"}
        if not valid:
            raise HTTPException(status_code=400, detail="File content does not match its video type or extension.")

    @classmethod
    async def _read_limited(cls, file: UploadFile, max_size_mb: int) -> bytes:
        limit = max_size_mb * 1024 * 1024

        async def read_chunks() -> bytes:
            chunks: list[bytes] = []
            total = 0
            while True:
                chunk = await file.read(min(cls.READ_CHUNK_SIZE, limit + 1 - total))
                if not chunk:
                    break
                chunks.append(chunk)
                total += len(chunk)
                if total > limit:
                    raise HTTPException(
                        status_code=400,
                        detail=f"File too large. Maximum size: {max_size_mb}MB",
                    )
            return b"".join(chunks)

        try:
            return await asyncio.wait_for(read_chunks(), timeout=cls.READ_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            raise HTTPException(
                status_code=408,
                detail=f"File read timed out after {cls.READ_TIMEOUT_SECONDS} seconds",
            ) from exc

    @classmethod
    def _validate_attachment_signature(cls, file: UploadFile, content: bytes) -> None:
        extension = cls._extension(file)
        content_type = file.content_type or ""
        if content_type.startswith("image/"):
            cls._validate_image_signature(file, content)
            return
        allowed_extensions = {
            "application/pdf": {".pdf"},
            "application/msword": {".doc"},
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
            "application/vnd.ms-excel": {".xls"},
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
            "application/vnd.ms-powerpoint": {".ppt"},
            "application/vnd.openxmlformats-officedocument.presentationml.presentation": {".pptx"},
            "application/zip": {".zip"},
            "application/x-zip-compressed": {".zip"},
            "text/plain": {".txt"},
        }
        if extension not in allowed_extensions.get(content_type, set()):
            raise HTTPException(status_code=400, detail="File extension does not match its attachment type.")
        if content_type == "application/pdf" and not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="File content does not match its attachment type.")
        if content_type in {"application/msword", "application/vnd.ms-excel", "application/vnd.ms-powerpoint"}:
            if not content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
                raise HTTPException(status_code=400, detail="File content does not match its attachment type.")
        if content_type in {
            "application/zip",
            "application/x-zip-compressed",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        } and not content.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
            raise HTTPException(status_code=400, detail="File content does not match its attachment type.")

    def __init__(
        self,
        tutor_repository: TutorRepository | None = None,
        student_repository: StudentRepository | None = None,
    ):
        self.tutor_repository = tutor_repository
        self.student_repository = student_repository

    async def validate_image(self, file: UploadFile, max_size_mb: int = 5) -> bytes:
        """Validate and read image file"""
        allowed_types = ["image/jpeg", "image/png", "image/jpg", "image/webp"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, detail="Invalid file type. Allowed: JPEG, PNG, WEBP"
            )

        file_content = await self._read_limited(file, max_size_mb)

        self._validate_image_signature(file, file_content)
        return file_content

    async def validate_video(self, file: UploadFile, max_size_mb: int = 100) -> bytes:
        """Validate and read video file."""
        allowed_types = ["video/mp4", "video/webm", "video/quicktime"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400, detail="Invalid file type. Allowed: MP4, WEBM, MOV"
            )

        file_content = await self._read_limited(file, max_size_mb)

        self._validate_video_signature(file, file_content)
        return file_content

    async def validate_service_attachment(
        self, file: UploadFile, max_size_mb: int = SERVICE_ATTACHMENT_MAX_MB
    ) -> bytes:
        allowed_types = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.ms-excel",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "application/vnd.ms-powerpoint",
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            "application/zip",
            "application/x-zip-compressed",
            "text/plain",
            "image/jpeg",
            "image/png",
            "image/webp",
        }
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail="Unsupported attachment type.",
            )
        if not file.filename:
            raise HTTPException(status_code=400, detail="A filename is required.")

        file_content = await self._read_limited(file, max_size_mb)
        self._validate_attachment_signature(file, file_content)
        return file_content

    async def upload_service_attachment(
        self, tutor_id: UUID, file: UploadFile
    ) -> tuple[str, int]:
        logger.info(
            "Service attachment validation started: filename={}, content_type={}, tutor_id={}",
            file.filename,
            file.content_type,
            tutor_id,
        )
        file_content = await self.validate_service_attachment(file)
        s3_key = s3_client.generate_s3_key(
            "service-attachments", file.filename, tutor_id
        )
        logger.info(
            "Service attachment validated: filename={}, bytes={}, s3_key={}",
            file.filename,
            len(file_content),
            s3_key,
        )
        if not s3_client.upload_file(file_content, s3_key, file.content_type):
            detail = s3_client.last_error or "Unknown S3 upload failure"
            logger.error(
                "Service attachment upload failed: filename={}, s3_key={}, reason={}",
                file.filename,
                s3_key,
                detail,
            )
            raise HTTPException(
                status_code=502,
                detail=f"Failed to upload file to S3: {detail}",
            )
        logger.info(
            "Service attachment upload completed: filename={}, s3_key={}",
            file.filename,
            s3_key,
        )
        return s3_key, len(file_content)

    async def upload_service_image(self, tutor_id: UUID, file: UploadFile) -> str:
        file_content = await self.validate_image(file, max_size_mb=self.SERVICE_IMAGE_MAX_MB)
        s3_key = s3_client.generate_s3_key("service-images", file.filename, tutor_id)
        s3_url = s3_client.upload_file(file_content, s3_key, file.content_type)
        if not s3_url:
            raise HTTPException(status_code=500, detail="Failed to upload image to S3")
        return s3_url

    async def upload_service_video(self, tutor_id: UUID, file: UploadFile) -> str:
        file_content = await self.validate_video(
            file, max_size_mb=self.SERVICE_VIDEO_MAX_MB
        )
        s3_key = s3_client.generate_s3_key("service-videos", file.filename, tutor_id)
        s3_url = s3_client.upload_file(file_content, s3_key, file.content_type)
        if not s3_url:
            raise HTTPException(status_code=500, detail="Failed to upload video to S3")
        return s3_url

    async def upload_profile_picture(
        self,
        tutor_id: UUID,
        file: UploadFile,
    ) -> str:
        async with get_session() as session:
            """Upload profile picture and update repository"""
            # Validate file
            file_content = await self.validate_image(file, max_size_mb=self.PROFILE_PICTURE_MAX_MB)

            # Get tutor and old picture URL
            tutor, old_profile_url, _ = (
                await self.tutor_repository.get_tutor_with_pictures(
                    tutor_id, session=session
                )
            )

            if not tutor:
                raise HTTPException(status_code=404, detail="Tutor not found")

            # Generate S3 key and upload
            s3_key = s3_client.generate_s3_key(
                "profile-picture", file.filename, tutor_id
            )
            s3_url = s3_client.upload_file(file_content, s3_key, file.content_type)

            if not s3_url:
                raise HTTPException(
                    status_code=500, detail="Failed to upload profile picture to S3"
                )

            # Update database
            updated_tutor = await self.tutor_repository.update_profile_picture(
                tutor_id, s3_url, session=session
            )

            if not updated_tutor:
                raise HTTPException(status_code=404, detail="Failed to update tutor")

            # Clean up old file from S3
            if old_profile_url:
                s3_client.delete_file(old_profile_url)

            await session.flush()
            await session.commit()

            return s3_url

    async def upload_cover_picture(
        self,
        tutor_id: UUID,
        file: UploadFile,
    ) -> str:
        async with get_session() as session:
            """Upload cover picture and update repository"""
            file_content = await self.validate_image(file, max_size_mb=self.COVER_PICTURE_MAX_MB)

            # Get tutor and old picture URL
            tutor, _, old_cover_url = (
                await self.tutor_repository.get_tutor_with_pictures(
                    tutor_id, session=session
                )
            )

            if not tutor:
                raise HTTPException(status_code=404, detail="Tutor not found")

            # Generate S3 key and upload
            s3_key = s3_client.generate_s3_key("cover-picture", file.filename, tutor_id)
            s3_url = s3_client.upload_file(file_content, s3_key, file.content_type)

            if not s3_url:
                raise HTTPException(
                    status_code=500, detail="Failed to upload cover picture to S3"
                )

            # Update database
            updated_tutor = await self.tutor_repository.update_cover_picture(
                tutor_id, s3_url, session=session
            )

            if not updated_tutor:
                raise HTTPException(status_code=404, detail="Failed to update tutor")

            # Clean up old file from S3
            if old_cover_url:
                s3_client.delete_file(old_cover_url)

            await session.flush()
            await session.commit()

            return s3_url

    async def delete_profile_picture(
        self,
        tutor_id: UUID,
    ) -> bool:
        async with get_session() as session:
            """Delete profile picture"""
            # Get tutor and old picture URL
            tutor, old_profile_url, _ = (
                await self.tutor_repository.get_tutor_with_pictures(
                    tutor_id, session=session
                )
            )

            if not tutor:
                raise HTTPException(status_code=404, detail="Tutor not found")

            if not old_profile_url:
                raise HTTPException(status_code=404, detail="No profile picture found")

            # Delete from S3
            if not s3_client.delete_file(old_profile_url):
                raise HTTPException(status_code=500, detail="Failed to delete from S3")

            # Delete URL from database
            success = await self.tutor_repository.delete_profile_picture_url(
                tutor_id, session=session
            )

            if not success:
                raise HTTPException(status_code=404, detail="Failed to update tutor")

            await session.flush()
            await session.commit()

            return True

    async def delete_cover_picture(
        self,
        tutor_id: str,
    ) -> bool:
        async with get_session() as session:
            """Delete cover picture"""
            # Get tutor and old picture URL
            tutor, _, old_cover_url = (
                await self.tutor_repository.get_tutor_with_pictures(
                    tutor_id, session=session
                )
            )

            if not tutor:
                raise HTTPException(status_code=404, detail="Tutor not found")

            if not old_cover_url:
                raise HTTPException(status_code=404, detail="No cover picture found")

            # Delete from S3
            if not s3_client.delete_file(old_cover_url):
                raise HTTPException(status_code=500, detail="Failed to delete from S3")

            # Delete URL from database
            success = await self.tutor_repository.delete_cover_picture_url(
                tutor_id, session=session
            )

            if not success:
                raise HTTPException(status_code=404, detail="Failed to update tutor")

            await session.flush()
            await session.commit()

            return True

    async def upload_student_profile_picture(
        self,
        student_id: UUID,
        file: UploadFile,
    ) -> str:
        async with get_session() as session:
            file_content = await self.validate_image(file, max_size_mb=self.PROFILE_PICTURE_MAX_MB)

            student, old_profile_url = await self.student_repository.get_student_with_picture(
                student_id,
                session=session,
            )

            if not student:
                raise HTTPException(status_code=404, detail="Student not found")

            s3_key = s3_client.generate_s3_key(
                "student-profile-picture", file.filename, student_id
            )
            s3_url = s3_client.upload_file(file_content, s3_key, file.content_type)

            if not s3_url:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to upload student profile picture to S3",
                )

            updated_student = await self.student_repository.update_profile_picture(
                student_id,
                s3_url,
                session=session,
            )

            if not updated_student:
                raise HTTPException(status_code=404, detail="Failed to update student")

            if old_profile_url:
                s3_client.delete_file(old_profile_url)

            await session.flush()
            await session.commit()

            return s3_url

    async def delete_student_profile_picture(
        self,
        student_id: UUID,
    ) -> bool:
        async with get_session() as session:
            student, old_profile_url = await self.student_repository.get_student_with_picture(
                student_id,
                session=session,
            )

            if not student:
                raise HTTPException(status_code=404, detail="Student not found")

            if not old_profile_url:
                raise HTTPException(status_code=404, detail="No profile picture found")

            if not s3_client.delete_file(old_profile_url):
                raise HTTPException(status_code=500, detail="Failed to delete from S3")

            success = await self.student_repository.delete_profile_picture_url(
                student_id,
                session=session,
            )

            if not success:
                raise HTTPException(status_code=404, detail="Failed to update student")

            await session.flush()
            await session.commit()

            return True

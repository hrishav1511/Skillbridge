from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.core.s3_client import s3_client
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.service_attachments import ServiceAttachment
from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation


class ServiceAttachmentRepository:
    async def is_tutor_owner(
        self, *, service_id: UUID, user_id: UUID, session: AsyncSession
    ) -> bool:
        result = await session.execute(
            select(Service.id)
            .join(
                UserRoleAssociation,
                UserRoleAssociation.tutor_id == Service.tutor_id,
            )
            .where(
                Service.id == service_id,
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.tutor_id.is_not(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def can_access(
        self, *, service_id: UUID, user_id: UUID, session: AsyncSession
    ) -> bool:
        owner = await self.is_tutor_owner(
            service_id=service_id, user_id=user_id, session=session
        )
        if owner:
            return True

        result = await session.execute(
            select(ServiceBooking.id)
            .join(
                UserRoleAssociation,
                UserRoleAssociation.student_id == ServiceBooking.student_id,
            )
            .where(
                ServiceBooking.service_id == service_id,
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.student_id.is_not(None),
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_service(
        self, *, service_id: UUID, user_id: UUID, session: AsyncSession
    ) -> Service | None:
        if not await self.can_access(
            service_id=service_id, user_id=user_id, session=session
        ):
            return None
        return (
            await session.execute(select(Service).where(Service.id == service_id))
        ).scalars().first()

    async def get_owned_service(
        self, *, service_id: UUID, user_id: UUID
    ) -> Service | None:
        async with get_session() as session:
            if not await self.is_tutor_owner(
                service_id=service_id, user_id=user_id, session=session
            ):
                return None
            return (
                await session.execute(select(Service).where(Service.id == service_id))
            ).scalars().first()

    async def list_for_service(
        self, *, service_id: UUID, user_id: UUID
    ) -> list[ServiceAttachment] | None:
        async with get_session() as session:
            if not await self.can_access(
                service_id=service_id, user_id=user_id, session=session
            ):
                return None
            return (
                await session.execute(
                    select(ServiceAttachment)
                    .where(ServiceAttachment.service_id == service_id)
                    .order_by(ServiceAttachment.created_at.desc())
                )
            ).scalars().all()

    async def get_for_user(
        self, *, attachment_id: UUID, user_id: UUID
    ) -> ServiceAttachment | None:
        async with get_session() as session:
            attachment = (
                await session.execute(
                    select(ServiceAttachment).where(
                        ServiceAttachment.id == attachment_id
                    )
                )
            ).scalars().first()
            if attachment is None or not await self.can_access(
                service_id=attachment.service_id,
                user_id=user_id,
                session=session,
            ):
                return None
            return attachment

    async def create(
        self,
        *,
        service_id: UUID,
        tutor_id: UUID,
        original_filename: str,
        content_type: str,
        file_size: int,
        object_key: str,
    ) -> ServiceAttachment:
        async with get_session() as session:
            attachment = ServiceAttachment(
                service_id=service_id,
                tutor_id=tutor_id,
                original_filename=original_filename,
                content_type=content_type,
                file_size=file_size,
                object_key=object_key,
            )
            session.add(attachment)
            await session.flush()
            await session.refresh(attachment)
            await session.commit()
            return attachment

    async def delete_for_tutor(
        self, *, attachment_id: UUID, user_id: UUID
    ) -> ServiceAttachment | None:
        async with get_session() as session:
            attachment = (
                await session.execute(
                    select(ServiceAttachment).where(
                        ServiceAttachment.id == attachment_id
                    )
                )
            ).scalars().first()
            if attachment is None or not await self.is_tutor_owner(
                service_id=attachment.service_id,
                user_id=user_id,
                session=session,
            ):
                return None
            await session.delete(attachment)
            await session.commit()
            return attachment

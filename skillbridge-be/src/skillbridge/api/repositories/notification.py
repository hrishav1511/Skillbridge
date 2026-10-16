from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.schemas.notification import NotificationOutput
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.utils.websocket import payloads as websocket_payloads
from skillbridge.utils.websocket.managers import manager


class NotificationRepository:
    async def create_for_user(
        self,
        *,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        data: dict | None,
        session: AsyncSession,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
            is_read=False,
            is_delivered=False,
        )
        session.add(notification)
        await session.flush()
        await session.refresh(notification)
        return notification

    async def admin_user_ids(self, *, session: AsyncSession) -> list[UUID]:
        result = await session.execute(
            select(UserRoleAssociation.user_id)
            .distinct()
            .join(Role, Role.id == UserRoleAssociation.role_id)
            .where(func.lower(Role.slug).in_(("admin", "super_admin")))
        )
        return list(result.scalars().all())

    @staticmethod
    def event_payload(notification: Notification) -> dict:
        return {
            "event": websocket_payloads.EVENT_NOTIFICATION,
            "payload": NotificationOutput.model_validate(notification).model_dump(mode="json"),
        }

    async def deliver_live(
        self,
        notification: Notification,
        *,
        alternate_connection_ids: list[UUID] | None = None,
    ) -> bool:
        """Best-effort delivery; the committed notification remains authoritative."""
        connection_ids = [notification.user_id, *(alternate_connection_ids or [])]
        for connection_id in dict.fromkeys(connection_ids):
            try:
                if await manager.send_to_user(
                    str(connection_id), self.event_payload(notification)
                ):
                    await self.mark_delivered(
                        notification_id=notification.id,
                        user_id=notification.user_id,
                    )
                    return True
            except Exception:
                continue
        return False

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        unread_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        async with get_session() as session:
            conditions = [Notification.user_id == user_id]
            if unread_only:
                conditions.append(Notification.is_read.is_(False))

            result = await session.execute(
                select(Notification)
                .where(*conditions)
                .order_by(Notification.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            notifications = result.scalars().all()
            total = (
                await session.execute(
                    select(func.count(Notification.id)).where(*conditions)
                )
            ).scalar_one()
            unread_count = (
                await session.execute(
                    select(func.count(Notification.id)).where(
                        Notification.user_id == user_id,
                        Notification.is_read.is_(False),
                    )
                )
            ).scalar_one()

            return {
                "success": True,
                "message": "Notifications fetched.",
                "metadata": {
                    "total": int(total or 0),
                    "unread_count": int(unread_count or 0),
                    "limit": limit,
                    "offset": offset,
                },
                "data": [NotificationOutput.model_validate(item) for item in notifications],
            }

    async def mark_read(self, *, notification_id: UUID, user_id: UUID) -> Notification | None:
        async with get_session() as session:
            notification = (
                await session.execute(
                    select(Notification).where(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
            ).scalars().first()
            if notification is None:
                return None
            notification.is_read = True
            await session.commit()
            return notification

    async def list_undelivered_for_user(
        self,
        *,
        user_id: UUID,
        limit: int = 100,
    ) -> list[NotificationOutput]:
        async with get_session() as session:
            result = await session.execute(
                select(Notification)
                .where(
                    Notification.user_id == user_id,
                    Notification.is_read.is_(False),
                    Notification.is_delivered.is_(False),
                )
                .order_by(Notification.created_at.asc())
                .limit(limit)
            )
            return [
                NotificationOutput.model_validate(notification)
                for notification in result.scalars().all()
            ]

    async def mark_delivered(
        self,
        *,
        notification_id: UUID,
        user_id: UUID,
    ) -> bool:
        async with get_session() as session:
            notification = (
                await session.execute(
                    select(Notification).where(
                        Notification.id == notification_id,
                        Notification.user_id == user_id,
                    )
                )
            ).scalars().first()
            if notification is None:
                return False
            notification.is_delivered = True
            await session.commit()
            return True

    async def mark_all_read(self, *, user_id: UUID) -> int:
        async with get_session() as session:
            notifications = (
                await session.execute(
                    select(Notification).where(
                        Notification.user_id == user_id,
                        Notification.is_read.is_(False),
                    )
                )
            ).scalars().all()
            for notification in notifications:
                notification.is_read = True
            await session.commit()
            return len(notifications)

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import inspect, select, desc, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.service import ServiceSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.services.moderation_service import moderate_service_content
from skillbridge.api.schemas.service import (
    ServiceBookingModel,
    ServiceModel,
    ServiceRevisionModel,
)
from skillbridge.api.validators.service import (
    CreateServiceInputValidator,
    UpdateServiceInputValidator,
    RevisionType,
)
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking
from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.utils.renderer import Status
from skillbridge.utils.websocket.managers import manager
from skillbridge.utils.websocket import payloads as websocket_payloads
from skillbridge.exceptions import (
    BaseExceptionMixin,
    NotFoundError,
    UnAuthorizedError,
)


class ServiceRepository(BaseRepository):
    model = Service
    search_filter = ServiceSearchFilter
    revision_model = ServiceRevision
    booking_model = ServiceBooking

    async def create_service(self, service_input: CreateServiceInputValidator):
        """
        Create a new service as a pending revision.
        Tutors create services, which start as PENDING revisions.
        """
        async with get_session() as session:
            moderation = await moderate_service_content(
                service_name=service_input.service_name,
                description=service_input.description,
                tags=service_input.tags,
            )
            # Create a pending revision for new service
            revision_data = {
                **service_input.model_dump(),
                "service_id": None,
                "approval_status": Status.PENDING,
                "rejection_reason": None,
                "revision_type": RevisionType.CREATE,
                "moderation_status": moderation.status,
                "moderation_flag": moderation.flagged,
                "moderation_categories": moderation.categories,
                "moderation_scores": moderation.scores,
                "moderation_reason": moderation.reason,
                "moderation_provider": moderation.provider,
                "moderated_at": moderation.moderated_at,
            }
            created_revision = await self.create(
                data=ServiceRevisionModel(**revision_data),
                model=self.revision_model,
                session=session,
                message="Service revision has been created.",
            )
            await session.commit()
            return created_revision

    async def get_service(self, service_id: UUID):
        """
        Get an approved/published service visible to students.
        """
        async with get_session() as session:
            query = (
                select(Service)
                .where(Service.id == service_id)
                .options(
                    joinedload(Service.service_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            service = result.scalars().first()
            if not service:
                raise NotFoundError(message="Service not found.", status_code=404)
            response = {
                "success": True,
                "message": "Service has been fetched.",
                "metadata": {},
                "data": service,
            }
            return response

    async def update_service(
        self,
        service_id: UUID,
        update_data: UpdateServiceInputValidator,
        tutor_id: Optional[UUID] = None,
    ):
        """
        Update a service by creating a new pending revision.
        The published service remains unchanged until admin approves.
        """
        async with get_session() as session:
            # Get the currently published service
            existing_service = await self.get(_id=service_id, session=session)
            service_data = existing_service["data"].to_dict()
            
            # Check if tutor owns this service
            if tutor_id and service_data["tutor_id"] != tutor_id:
                raise UnAuthorizedError(
                    message="Tutors can only update their own services.",
                    status_code=403,
                )
            
            # Apply updates to service data
            updated_values = {
                key: value
                for key, value in update_data.model_dump().items()
                if value is not None
            }

            moderation = await moderate_service_content(
                service_name=updated_values.get("service_name", service_data["service_name"]),
                description=updated_values.get("description", service_data.get("description")),
                tags=updated_values.get("tags", service_data.get("tags")),
            )
            
            # Create new pending revision
            revision_payload = {
                **service_data,
                **updated_values,
                "service_id": service_id,
                "tutor_id": service_data["tutor_id"],
                "approval_status": Status.PENDING,
                "rejection_reason": None,
                "revision_type": RevisionType.UPDATE,
                "moderation_status": moderation.status,
                "moderation_flag": moderation.flagged,
                "moderation_categories": moderation.categories,
                "moderation_scores": moderation.scores,
                "moderation_reason": moderation.reason,
                "moderation_provider": moderation.provider,
                "moderated_at": moderation.moderated_at,
            }
            
            # Check if there's already a pending revision
            pending_revision = await self._get_pending_revision_for_service(
                service_id=service_id, 
                session=session
            )
            if pending_revision:
                # Delete the old pending revision and create a new one
                await session.delete(pending_revision)
                await session.flush()
            
            updated_revision = await self.create(
                data=ServiceRevisionModel(**revision_payload),
                model=self.revision_model,
                session=session,
                message="Service revision has been created.",
            )
            await session.commit()
            return updated_revision

    async def delete_service(self, service_id: UUID, tutor_id: Optional[UUID] = None):
        """
        Delete a service by creating a DELETE revision.
        """
        async with get_session() as session:
            existing_service = await self.get(_id=service_id, session=session)
            service_data = existing_service["data"].to_dict()
            
            # Check if tutor owns this service
            if tutor_id and service_data["tutor_id"] != tutor_id:
                raise UnAuthorizedError(
                    message="Tutors can only delete their own services.",
                    status_code=403,
                )
            
            # Create a DELETE revision
            revision_payload = {
                **service_data,
                "service_id": service_id,
                "tutor_id": service_data["tutor_id"],
                "approval_status": Status.PENDING,
                "rejection_reason": None,
                "revision_type": RevisionType.DELETE,
            }
            
            deleted_revision = await self.create(
                data=ServiceRevisionModel(**revision_payload),
                model=self.revision_model,
                session=session,
                message="Service deletion revision has been created.",
            )
            await session.commit()
            return deleted_revision

    async def _check_admin_access(
        self,
        user_id: UUID,
        session: AsyncSession,
    ) -> bool:
        """Return True when the user is associated with an admin role."""
        query = (
            select(UserRoleAssociation)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                func.lower(Role.slug) == "admin",
            )
        )
        result = await session.execute(query)
        return result.scalars().first() is not None

    def _revision_to_dict(self, revision_obj: ServiceRevision) -> dict:
        """Return a plain dict from the loaded ORM state to avoid lazy-load errors."""
        state = inspect(revision_obj)
        loaded_values = state.dict or {}
        revision_data = {
            column.key: loaded_values.get(column.key)
            for column in revision_obj.__table__.columns
        }

        tutor = None
        relation_state = state.attrs.service_revision_tutor
        if relation_state.loaded_value is not None:
            tutor_relation = relation_state.value
            if tutor_relation and tutor_relation.tutor_ura:
                user = tutor_relation.tutor_ura[0].ura_user if tutor_relation.tutor_ura else None
                if user:
                    tutor = {
                        "full_name": user.full_name,
                        "email": user.email,
                        "id": user.id,
                    }
        revision_data["tutor"] = tutor
        return revision_data

    async def get_pending_revisions(self, limit: int = 100, offset: int = 0,):
        """
        Get all pending revisions for admin approval.
        """
        async with get_session() as session:
            

            query = (
                select(ServiceRevision)
                .where(ServiceRevision.approval_status == Status.PENDING)
                .order_by(desc(ServiceRevision.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(ServiceRevision.service_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            revisions = result.scalars().unique().all()
            revision_dicts = [self._revision_to_dict(revision) for revision in revisions]
            
            # Get total count
            count_query = select(ServiceRevision).where(
                ServiceRevision.approval_status == Status.PENDING
            )
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            
            return {
                "success": True,
                "message": "Pending revisions fetched.",
                "data": revision_dicts,
                "metadata": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }

    async def approve_revision(
        self,
        revision_id: UUID,
        user_id: UUID,
        override_moderation: bool = True,
    ):
        """
        Approve a revision and make it the published service.
        """
        async with get_session() as session:

            if not await self._check_admin_access(user_id=user_id, session=session):
                raise UnAuthorizedError(message="Admin access required.", status_code=403)
            
            # Load the revision and related tutor data while the session is open
            query = (
                select(ServiceRevision)
                .where(ServiceRevision.id == revision_id)
                .options(
                    joinedload(ServiceRevision.service_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            revision_obj = result.scalars().first()
            if not revision_obj:
                raise NotFoundError(message="Revision not found.", status_code=404)

            # Check if already approved or rejected
            if revision_obj.approval_status != Status.PENDING:
                raise BaseExceptionMixin(
                    f"Revision is already {revision_obj.approval_status}.",
                    status_code=409,
                )
            print(f"Revision moderation status: {revision_obj.moderation_status}, override: {override_moderation}")
            if revision_obj.moderation_status in {"FLAGGED", "ERROR"} and not override_moderation:
                raise BaseExceptionMixin(
                    "Revision requires moderation review or an explicit admin override.",
                    status_code=409,
                )

            service = None
            
            # Handle based on revision type
            if revision_obj.revision_type == RevisionType.CREATE:
                # Create new service from this revision
                new_service_data = {
                    "id": revision_obj.id,
                    "tutor_id": revision_obj.tutor_id,
                    "service_name": revision_obj.service_name,
                    "description": revision_obj.description,
                    "date": revision_obj.date,
                    "time": revision_obj.time,
                    "end_time": revision_obj.end_time,
                    "price": revision_obj.price,
                    "level": revision_obj.level,
                    "joining_link": revision_obj.joining_link,
                    "image_urls": revision_obj.image_urls,
                    "video_url": revision_obj.video_url,
                    "video_urls": revision_obj.video_urls,
                    "tags": revision_obj.tags,
                }
                new_service = Service(**new_service_data)
                session.add(new_service)
                await session.flush()
                # Update revision's service_id
                revision_obj.service_id = new_service.id
                
            elif revision_obj.revision_type == RevisionType.UPDATE:
                # Update the published service
                service = await session.get(Service, revision_obj.service_id)
                if not service:
                    raise NotFoundError(message="Service not found.", status_code=404)
                
                service.service_name = revision_obj.service_name
                service.description = revision_obj.description
                service.date = revision_obj.date
                service.time = revision_obj.time
                service.end_time = revision_obj.end_time
                service.price = revision_obj.price
                service.level = revision_obj.level
                service.joining_link = revision_obj.joining_link
                service.image_urls = revision_obj.image_urls
                service.video_url = revision_obj.video_url
                service.video_urls = revision_obj.video_urls
                service.tags = revision_obj.tags
                # Update the published service
                service = await session.get(Service, revision_obj.service_id)
                if not service:
                    raise NotFoundError(message="Service not found.", status_code=404)
                
                service.service_name = revision_obj.service_name
                service.description = revision_obj.description
                service.date = revision_obj.date
                service.time = revision_obj.time
                service.end_time = revision_obj.end_time
                service.price = revision_obj.price
                service.level = revision_obj.level
                service.joining_link = revision_obj.joining_link
                service.image_urls = revision_obj.image_urls
                service.video_url = revision_obj.video_url
                service.video_urls = revision_obj.video_urls
                
            elif revision_obj.revision_type == RevisionType.DELETE:
                # Delete the published service
                service = await session.get(Service, revision_obj.service_id)
                if service:
                    await session.delete(service)
            
            # Update revision status to ACCEPTED
            revision_obj.approval_status = Status.ACCEPTED
            
            revision_data = self._revision_to_dict(revision_obj)
            tutor_user_id = (
                await session.execute(
                    select(UserRoleAssociation.user_id).where(
                        UserRoleAssociation.tutor_id == revision_obj.tutor_id,
                    )
                )
            ).scalar_one_or_none()
            notification = None
            student_notification_events = []
            student_user_ids = []
            if (
                revision_obj.revision_type == RevisionType.UPDATE
                and revision_obj.service_id is not None
                and service is not None
                and datetime.combine(service.date, service.time) > datetime.now()
            ):
                student_user_ids = list(
                    (
                        await session.execute(
                            select(UserRoleAssociation.user_id)
                            .distinct()
                            .join(
                                ServiceBooking,
                                ServiceBooking.student_id
                                == UserRoleAssociation.student_id,
                            )
                            .where(
                                ServiceBooking.service_id == revision_obj.service_id,
                                UserRoleAssociation.student_id.is_not(None),
                            )
                        )
                    ).scalars().all()
                )
                for student_user_id in student_user_ids:
                    student_notification = await NotificationRepository().create_for_user(
                        user_id=student_user_id,
                        notification_type="SERVICE_UPDATED",
                        title="Booked service updated",
                        message=(
                            f"The service '{revision_obj.service_name}' you booked "
                            "has been updated."
                        ),
                        data={
                            "revision_id": str(revision_obj.id),
                            "service_id": str(revision_obj.service_id),
                            "revision_type": str(revision_obj.revision_type),
                        },
                        session=session,
                    )
                    student_notification_events.append(
                        (
                            student_user_id,
                            {
                                "event": websocket_payloads.EVENT_NOTIFICATION,
                                "payload": {
                                    "id": str(student_notification.id),
                                    "user_id": str(student_notification.user_id),
                                    "notification_type": student_notification.notification_type,
                                    "title": student_notification.title,
                                    "message": student_notification.message,
                                    "data": student_notification.data,
                                    "is_read": student_notification.is_read,
                                    "created_at": student_notification.created_at.isoformat()
                                    if student_notification.created_at
                                    else None,
                                },
                            },
                        )
                    )
            if tutor_user_id is not None:
                notification_type = (
                    "SERVICE_APPROVED"
                    if revision_obj.revision_type == RevisionType.CREATE
                    else "SERVICE_REVISION_APPROVED"
                )
                notification = await NotificationRepository().create_for_user(
                    user_id=tutor_user_id,
                    notification_type=notification_type,
                    title="Service approved",
                    message=(
                        f"Your service '{revision_obj.service_name}' was approved."
                        if revision_obj.revision_type == RevisionType.CREATE
                        else f"Your service revision '{revision_obj.service_name}' was approved."
                    ),
                    data={
                        "revision_id": str(revision_obj.id),
                        "service_id": str(revision_obj.service_id)
                        if revision_obj.service_id
                        else None,
                        "revision_type": str(revision_obj.revision_type),
                    },
                    session=session,
                )
                notification_event = {
                    "event": websocket_payloads.EVENT_NOTIFICATION,
                    "payload": {
                        "id": str(notification.id),
                        "user_id": str(notification.user_id),
                        "notification_type": notification.notification_type,
                        "title": notification.title,
                        "message": notification.message,
                        "data": notification.data,
                        "is_read": notification.is_read,
                        "created_at": notification.created_at.isoformat()
                        if notification.created_at
                        else None,
                    },
                }
            await session.commit()

            if notification is not None:
                try:
                    delivery_ids = {str(tutor_user_id)}
                    if revision_obj.tutor_id is not None:
                        delivery_ids.add(str(revision_obj.tutor_id))
                    delivered = False
                    for connection_id in delivery_ids:
                        if await manager.send_to_user(connection_id, notification_event):
                            delivered = True
                            await NotificationRepository().mark_delivered(
                                notification_id=notification.id,
                                user_id=tutor_user_id,
                            )
                            break
                    if not delivered:
                        print(
                            "Notification persisted; tutor WebSocket is offline. "
                            f"Tried connection IDs: {sorted(delivery_ids)}"
                        )
                except Exception as exc:
                    # Realtime delivery is best effort; the committed row is the source of truth.
                    print(
                        "Notification persisted, but realtime delivery failed: "
                        f"{tutor_user_id}: {exc!r}"
                    )

            for student_user_id, student_event in student_notification_events:
                try:
                    if await manager.send_to_user(str(student_user_id), student_event):
                        await NotificationRepository().mark_delivered(
                            notification_id=UUID(student_event["payload"]["id"]),
                            user_id=student_user_id,
                        )
                except Exception as exc:
                    print(
                        "Student service-update notification persisted, but "
                        f"realtime delivery failed for {student_user_id}: {exc!r}"
                    )
            
            return {
                "success": True,
                "message": f"Revision approved and {revision_obj.revision_type.lower()} applied.",
                "data": revision_data,
            }

    async def reject_revision(self, revision_id: UUID, rejection_reason: str):
        """
        Reject a revision. The published service remains unchanged.
        """
        async with get_session() as session:
            query = (
                select(ServiceRevision)
                .where(ServiceRevision.id == revision_id)
                .options(
                    joinedload(ServiceRevision.service_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            revision_obj = result.scalars().first()
            if not revision_obj:
                raise NotFoundError(message="Revision not found.", status_code=404)
            
            # Check if already approved or rejected
            if revision_obj.approval_status != Status.PENDING:
                raise BaseExceptionMixin(
                    f"Revision is already {revision_obj.approval_status}.",
                    status_code=409,
                )
            
            # Update revision status to REJECTED with reason
            revision_obj.approval_status = Status.REJECTED
            revision_obj.rejection_reason = rejection_reason

            tutor_user_id = (
                await session.execute(
                    select(UserRoleAssociation.user_id).where(
                        UserRoleAssociation.tutor_id == revision_obj.tutor_id,
                    )
                )
            ).scalar_one_or_none()

            notification = None
            if tutor_user_id is not None:
                notification_type = (
                    "SERVICE_REJECTED"
                    if revision_obj.revision_type == RevisionType.CREATE
                    else "SERVICE_REVISION_REJECTED"
                )
                notification = await NotificationRepository().create_for_user(
                    user_id=tutor_user_id,
                    notification_type=notification_type,
                    title=(
                        "Service rejected"
                        if revision_obj.revision_type == RevisionType.CREATE
                        else "Service revision rejected"
                    ),
                    message=(
                        f"Your service '{revision_obj.service_name}' was rejected. Reason: {rejection_reason}."
                        if revision_obj.revision_type == RevisionType.CREATE
                        else f"Your service revision '{revision_obj.service_name}' was rejected. Reason: {rejection_reason}."
                    ),
                    data={
                        "revision_id": str(revision_obj.id),
                        "service_id": str(revision_obj.service_id)
                        if revision_obj.service_id
                        else None,
                        "revision_type": str(revision_obj.revision_type),
                        "rejection_reason": rejection_reason,
                    },
                    session=session,
                )
                notification_event = {
                    "event": websocket_payloads.EVENT_NOTIFICATION,
                    "payload": {
                        "id": str(notification.id),
                        "user_id": str(notification.user_id),
                        "notification_type": notification.notification_type,
                        "title": notification.title,
                        "message": notification.message,
                        "data": notification.data,
                        "is_read": notification.is_read,
                        "created_at": notification.created_at.isoformat()
                        if notification.created_at
                        else None,
                    },
                }

            revision_data = self._revision_to_dict(revision_obj)
            await session.commit()

            if notification is not None:
                try:
                    delivery_ids = {str(tutor_user_id)}
                    if revision_obj.tutor_id is not None:
                        delivery_ids.add(str(revision_obj.tutor_id))
                    delivered = False
                    for connection_id in delivery_ids:
                        if await manager.send_to_user(connection_id, notification_event):
                            delivered = True
                            await NotificationRepository().mark_delivered(
                                notification_id=notification.id,
                                user_id=tutor_user_id,
                            )
                            break
                    if not delivered:
                        print(
                            "Notification persisted; tutor WebSocket is offline. "
                            f"Tried connection IDs: {sorted(delivery_ids)}"
                        )
                except Exception as exc:
                    print(
                        "Notification persisted, but realtime delivery failed: "
                        f"{tutor_user_id}: {exc!r}"
                    )

            return {
                "success": True,
                "message": "Revision rejected.",
                "data": revision_data,
            }

    async def get_tutor_services(
        self,
        tutor_id: UUID,
        approval_status: Status | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """
        Get services by a specific tutor.
        """
        async with get_session() as session:
            conditions = [Service.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                conditions.append(Service.approval_status == str(approval_status).upper())

            query = (
                select(Service)
                .where(*conditions)
                .order_by(desc(Service.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(Service.service_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            services = result.scalars().unique().all()
            count_conditions = [Service.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                count_conditions.append(Service.approval_status == str(approval_status).upper())

            count_query = select(Service).where(*count_conditions)
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            
            return {
                "success": True,
                "message": "Tutor services fetched.",
                "data": services,
                "metadata": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }

    async def get_tutor_revisions(
        self,
        tutor_id: UUID,
        approval_status: Status | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        """
        Get revisions created by a specific tutor.
        """
        async with get_session() as session:
            conditions = [ServiceRevision.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                conditions.append(ServiceRevision.approval_status == str(approval_status).upper())

            query = (
                select(ServiceRevision)
                .where(*conditions)
                .order_by(desc(ServiceRevision.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(ServiceRevision.service_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            revisions = result.scalars().unique().all()
            
            # Get total count
            count_conditions = [ServiceRevision.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                count_conditions.append(
                    ServiceRevision.approval_status == str(approval_status).upper()
                )
            count_query = select(ServiceRevision).where(*count_conditions)
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            
            return {
                "success": True,
                "message": "Tutor revisions fetched.",
                "data": revisions,
                "metadata": {
                    "total": total,
                    "limit": limit,
                    "offset": offset,
                },
            }

    async def _get_pending_revision_for_service(
        self, 
        service_id: UUID, 
        session: AsyncSession,
    ) -> Optional[ServiceRevision]:
        """
        Helper method to get any pending revision for a service.
        """
        query = (
            select(ServiceRevision)
            .where(
                and_(
                    ServiceRevision.service_id == service_id,
                    ServiceRevision.approval_status == Status.PENDING,
                )
            )
        )
        result = await session.execute(query)
        return result.scalars().first()

    async def get_admin_services(self, limit: int = 100, offset: int = 0):
        """Every service, disabled ones included.

        The student-facing listing filters to ACTIVE rows, so moderation needs
        its own query - otherwise a service could be disabled and then never
        found again to re-enable it.
        """
        async with get_session() as session:
            query = (
                select(Service)
                .order_by(desc(Service.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(Service.service_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            services = result.scalars().unique().all()
            count = await session.execute(select(func.count(Service.id)))
            return {
                "success": True,
                "message": "Services fetched.",
                "metadata": {
                    "total": int(count.scalar_one() or 0),
                    "limit": limit,
                    "offset": offset,
                },
                "data": services,
            }

    async def set_service_status(self, service_id: UUID, service_status: str):
        """Enable or disable a service.

        Disabling is the same state the report-driven disable already uses, so
        a service disabled here drops out of the student listing through the
        existing ``public_only`` ACTIVE filter.
        """
        async with get_session() as session:
            service = await session.get(Service, service_id)
            if service is None:
                raise NotFoundError(message="Service not found.", status_code=404)
            service.status = service_status
            await session.flush()
            await session.commit()
            return service

    async def get_accepted_booking_counts(
        self, service_ids: list[UUID]
    ) -> dict[UUID, int]:
        """Accepted bookings per service - the enrolment count.

        The service detail view counts ACCEPTED bookings, so the listing has to
        use the same rule or the two disagree. Counted in one query for the
        whole page rather than once per row.
        """
        if not service_ids:
            return {}
        async with get_session() as session:
            rows = await session.execute(
                select(ServiceBooking.service_id, func.count(ServiceBooking.id))
                .where(
                    ServiceBooking.service_id.in_(service_ids),
                    func.upper(ServiceBooking.status) == "ACCEPTED",
                )
                .group_by(ServiceBooking.service_id)
            )
            return {service_id: count for service_id, count in rows.all()}

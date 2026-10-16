from typing import Optional, Tuple
from uuid import UUID

from sqlalchemy import desc, func, inspect, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from skillbridge.api.services.moderation_service import moderate_tutor_content

from skillbridge.api.filters.tutor import TutorSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.notification import NotificationRepository
from skillbridge.api.repositories.user import UserRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.schemas.tutor import TutorModel, TutorRevisionModel
from skillbridge.api.schemas.user import UpdateUserModel
from skillbridge.api.validators.service import RevisionType
from skillbridge.api.validators.tutor import (
    CreateTutorInputValidator,
    UpdateTutorInputValidator,
)
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.tutor_revisions import TutorRevision
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.utils.renderer import Status
from skillbridge.exceptions import (
    BaseExceptionMixin,
    NotFoundError,
    UnAuthorizedError,
)


class TutorRepository(BaseRepository):
    model = Tutor
    search_filter = TutorSearchFilter
    revision_model = TutorRevision

    async def create_tutor(
        self,
        register_data: UserRegisterInputValidator,
        session: AsyncSession = None,
    ):
        if session is None:
            async with get_session() as create_session:
                tutor = await self.create_tutor(
                    register_data=register_data,
                    session=create_session,
                )
                await create_session.commit()
                return tutor

        tutor = await self.create(
            data=TutorModel(**register_data.model_dump()),
            session=session,
        )
        tutor_obj = tutor["data"]

        moderation = await moderate_tutor_content(
            academic_program=tutor_obj.academic_program,
            bio=tutor_obj.bio,
            tags=tutor_obj.tags,
        )

        revision_payload = {
            "tutor_id": tutor_obj.id,
            "full_name": getattr(register_data, "full_name", None),
            "academic_program": tutor_obj.academic_program,
            "bio": tutor_obj.bio,
            "phone": tutor_obj.phone,
            "teaching_style": tutor_obj.teaching_style,
            "is_visible": tutor_obj.is_visible,
            "accepting_requests": tutor_obj.accepting_requests,
            "tags": tutor_obj.tags,
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

        await self.create(
            data=TutorRevisionModel(**revision_payload),
            model=self.revision_model,
            session=session,
            message="Tutor creation revision has been created.",
        )

        return tutor

    async def create_tutor_registration_request(
        self,
        register_data: UserRegisterInputValidator,
        user_id: UUID,
        session: AsyncSession = None,
    ):
        moderation = await moderate_tutor_content(
            academic_program=register_data.academic_program,
            bio=register_data.bio,
            tags=register_data.tags,
        )
        revision_payload = {
            "tutor_id": None,
            "user_id": user_id,
            "full_name": getattr(register_data, "full_name", None),
            "academic_program": register_data.academic_program,
            "bio": register_data.bio,
            "phone": register_data.phone,
            "teaching_style": register_data.teaching_style,
            "is_visible": True if register_data.is_visible is None else register_data.is_visible,
            "accepting_requests": register_data.accepting_requests,
            "tags": register_data.tags,
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

        if session is None:
            async with get_session() as create_session:
                revision = await self.create(
                    data=TutorRevisionModel(**revision_payload),
                    model=self.revision_model,
                    session=create_session,
                    message="Tutor registration revision has been created.",
                )
                await create_session.commit()
                return revision
        revision = await self.create(
            data=TutorRevisionModel(**revision_payload),
            model=self.revision_model,
            session=session,
            message="Tutor registration revision has been created.",
        )
        return revision

    async def create_tutor_profile(
        self,
        tutor_input: CreateTutorInputValidator,
        session: AsyncSession = None,
    ):
        if session is None:
            async with get_session() as create_session:
                tutor = await self.create_tutor_profile(
                    tutor_input=tutor_input,
                    session=create_session,
                )
                await create_session.commit()
                return tutor

        tutor = await self.create(
            data=TutorModel(**tutor_input.model_dump()),
            session=session,
        )
        tutor_obj = tutor["data"]

        moderation = await moderate_tutor_content(
            academic_program=tutor_obj.academic_program,
            bio=tutor_obj.bio,
            tags=tutor_obj.tags,
        )

        revision_payload = {
            "tutor_id": tutor_obj.id,
            "full_name": None,
            "academic_program": tutor_obj.academic_program,
            "bio": tutor_obj.bio,
            "phone": tutor_obj.phone,
            "teaching_style": tutor_obj.teaching_style,
            "is_visible": tutor_obj.is_visible,
            "accepting_requests": tutor_obj.accepting_requests,
            "tags": tutor_obj.tags,
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

        await self.create(
            data=TutorRevisionModel(**revision_payload),
            model=self.revision_model,
            session=session,
            message="Tutor creation revision has been created.",
        )

        return tutor

    async def create_tutor_revision(
        self,
        tutor_id: UUID | None,
        full_name: str | None,
        update_data: UpdateTutorInputValidator,
        session: AsyncSession = None,
    ):
        if session is None:
            async with get_session() as session:
                return await self.create_tutor_revision(
                    tutor_id=tutor_id,
                    full_name=full_name,
                    update_data=update_data,
                    session=session,
                )

        tutor_response = await self.get(_id=tutor_id, session=session)
        tutor_obj = tutor_response["data"]
        current_data = {
            "academic_program": tutor_obj.academic_program,
            "bio": tutor_obj.bio,
            "phone": tutor_obj.phone,
            "teaching_style": tutor_obj.teaching_style,
            "is_visible": tutor_obj.is_visible,
            "accepting_requests": tutor_obj.accepting_requests,
            "tags": tutor_obj.tags,
            "approval_status": tutor_obj.approval_status,
        }
        updated_values = {
            key: value
            for key, value in update_data.model_dump().items()
            if value is not None
        }

        moderation_inputs = {
            "academic_program": current_data.get("academic_program"),
            "bio": current_data.get("bio"),
            "tags": current_data.get("tags"),
        }
        for field in ("academic_program", "bio", "tags"):
            if field in updated_values:
                moderation_inputs[field] = updated_values[field]

        moderation = await moderate_tutor_content(
            academic_program=moderation_inputs["academic_program"],
            bio=moderation_inputs["bio"],
            tags=moderation_inputs["tags"],
        )

        revision_payload = {
            **current_data,
            **updated_values,
            "tutor_id": tutor_id,
            "full_name": full_name,
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

        pending_revision = await self._get_pending_revision_for_tutor(
            tutor_id=tutor_id, session=session
        )
        if pending_revision:
            await session.delete(pending_revision)
            await session.flush()

        created_revision = await self.create(
            data=TutorRevisionModel(**revision_payload),
            model=self.revision_model,
            session=session,
            message="Tutor revision has been created.",
        )
        await session.commit()
        return created_revision

    async def list_academic_programs(self) -> list[str]:
        """Distinct academic programs across tutors students can actually see.

        Backs the filter dropdown. Deriving the options from a page of results
        would hide any program whose only tutors fall on a later page, so the
        list is computed over the whole visible set instead.
        """
        async with get_session() as session:
            query = (
                select(Tutor.academic_program)
                .where(
                    Tutor.academic_program.is_not(None),
                    Tutor.academic_program != "",
                    Tutor.is_visible.is_(True),
                    func.upper(Tutor.status) == "ACTIVE",
                    func.upper(Tutor.approval_status).in_(("ACCEPTED", "APPROVED")),
                )
                .distinct()
            )
            rows = (await session.execute(query)).scalars().all()

        # Collapse case and spacing differences so the dropdown does not show
        # "Computer Science" and "computer science" as separate options.
        seen: dict[str, str] = {}
        for row in rows:
            label = str(row).strip()
            if label and label.casefold() not in seen:
                seen[label.casefold()] = label
        return sorted(seen.values(), key=str.casefold)

    async def list_tags(self) -> list[str]:
        """Distinct subject tags across tutors students can actually see.

        Same reasoning as list_academic_programs: computed over the whole
        visible set so a tag is never missing from the dropdown just because
        its tutors are on a later page.
        """
        async with get_session() as session:
            query = select(Tutor.tags).where(
                Tutor.tags.is_not(None),
                Tutor.is_visible.is_(True),
                func.upper(Tutor.status) == "ACTIVE",
                func.upper(Tutor.approval_status).in_(("ACCEPTED", "APPROVED")),
            )
            rows = (await session.execute(query)).scalars().all()

        seen: dict[str, str] = {}
        for row in rows:
            for tag in row or []:
                label = str(tag).strip()
                if label and label.casefold() not in seen:
                    seen[label.casefold()] = label
        return sorted(seen.values(), key=str.casefold)

    async def update_visibility(self, tutor_id: UUID, user_id: UUID, is_visible: bool):
        async with get_session() as session:
            association = await session.execute(
                select(UserRoleAssociation).where(
                    UserRoleAssociation.user_id == user_id,
                    UserRoleAssociation.tutor_id == tutor_id,
                )
            )
            if association.scalars().first() is None:
                raise UnAuthorizedError(
                    message="You can update only your own tutor profile.",
                    status_code=403,
                )
            tutor = await session.get(Tutor, tutor_id)
            if tutor is None:
                raise NotFoundError(message="Tutor not found.", status_code=404)
            tutor.is_visible = is_visible
            await session.commit()
            return tutor

    async def update_availability(self, tutor_id: UUID, user_id: UUID, accepting_requests: bool):
        async with get_session() as session:
            association = await session.execute(
                select(UserRoleAssociation).where(
                    UserRoleAssociation.user_id == user_id,
                    UserRoleAssociation.tutor_id == tutor_id,
                )
            )
            if association.scalars().first() is None:
                raise UnAuthorizedError(
                    message="You can update only your own tutor profile.",
                    status_code=403,
                )
            tutor = await session.get(Tutor, tutor_id)
            if tutor is None:
                raise NotFoundError(message="Tutor not found.", status_code=404)
            tutor.accepting_requests = accepting_requests
            await session.commit()
            return tutor

    async def get_filter_options(self):
        async with get_session() as session:
            academic_programs = (
                await session.execute(
                    select(Tutor.academic_program)
                    .where(Tutor.academic_program.is_not(None))
                    .distinct()
                    .order_by(Tutor.academic_program.asc())
                )
            ).scalars().all()
            teaching_styles = (
                await session.execute(
                    select(Tutor.teaching_style)
                    .where(Tutor.teaching_style.is_not(None))
                    .distinct()
                    .order_by(Tutor.teaching_style.asc())
                )
            ).scalars().all()
            return {
                "academic_programs": list(academic_programs),
                "teaching_styles": list(teaching_styles),
            }

    async def get_pending_tutor_revisions(
        self, user_id: UUID, limit: int = 100, offset: int = 0
    ):
        async with get_session() as session:
            if not await UserRoleAssociationRepository().is_user_admin(
                user_id=user_id, session=session
            ):
                raise UnAuthorizedError(message="Admin access required.", status_code=403)

            query = (
                select(TutorRevision)
                .where(TutorRevision.approval_status == Status.PENDING)
                .order_by(desc(TutorRevision.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(TutorRevision.tutor_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user),
                    joinedload(TutorRevision.tutor_revision_user),
                )
            )
            result = await session.execute(query)
            revisions = result.scalars().unique().all()
            revision_dicts = [self._revision_to_dict(revision) for revision in revisions]
            count_query = select(TutorRevision).where(
                TutorRevision.approval_status == Status.PENDING
            )
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            return {
                "success": True,
                "message": "Pending tutor revisions fetched.",
                "data": revision_dicts,
                "metadata": {"total": total, "limit": limit, "offset": offset},
            }

    async def get_admin_tutors(self, limit: int = 100, offset: int = 0):
        async with get_session() as session:
            query = (
                select(Tutor)
                .join(UserRoleAssociation, UserRoleAssociation.tutor_id == Tutor.id)
                .join(Role, UserRoleAssociation.role_id == Role.id)
                .join(User, UserRoleAssociation.user_id == User.id)
                .where(func.lower(Role.slug) == "tutor")
                .order_by(desc(Tutor.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(Tutor.tutor_ura).joinedload(UserRoleAssociation.ura_user)
                )
            )
            result = await session.execute(query)
            tutors = result.scalars().unique().all()
            count = await session.execute(
                select(func.count(Tutor.id))
                .join(UserRoleAssociation, UserRoleAssociation.tutor_id == Tutor.id)
                .join(Role, UserRoleAssociation.role_id == Role.id)
                .where(func.lower(Role.slug) == "tutor")
            )
            return {
                "success": True,
                "message": "Tutors fetched.",
                "metadata": {"total": int(count.scalar_one() or 0), "limit": limit, "offset": offset},
                "data": tutors,
            }

    async def set_account_status(
        self,
        tutor_id: UUID,
        account_status: str,
    ):
        """Deactivate the tutor's marketplace presence, not their login.

        Deactivation removes a tutor from browsing, search, booking and chat -
        it is not an account ban. Flipping ``User.status`` did both at once and
        locked the tutor out of their own account, so the state lives on the
        Tutor row, which every public query already filters on. A genuine
        account ban is a separate action on ``User.status``.
        """
        async with get_session() as session:
            association = (
                await session.execute(
                    select(UserRoleAssociation)
                    .join(Role, UserRoleAssociation.role_id == Role.id)
                    .where(
                        UserRoleAssociation.tutor_id == tutor_id,
                        func.lower(Role.slug) == "tutor",
                    )
                )
            ).scalars().first()
            if association is None:
                raise NotFoundError(message="Tutor account not found.", status_code=404)
            tutor = await session.get(Tutor, tutor_id)
            if tutor is None:
                raise NotFoundError(message="Tutor account not found.", status_code=404)
            tutor.status = account_status
            await session.commit()
            await session.refresh(tutor)
            return tutor

    async def approve_tutor_revision(self, revision_id: UUID, user_id: UUID):
        async with get_session() as session:
            if not await UserRoleAssociationRepository().is_user_admin(
                user_id=user_id, session=session
            ):
                raise UnAuthorizedError(message="Admin access required.", status_code=403)

            query = select(TutorRevision).where(TutorRevision.id == revision_id).options(
                joinedload(TutorRevision.tutor_revision_tutor)
                .joinedload(Tutor.tutor_ura)
                .joinedload(UserRoleAssociation.ura_user)
            )
            result = await session.execute(query)
            revision_obj = result.scalars().first()
            if not revision_obj:
                raise NotFoundError(message="Revision not found.", status_code=404)
            if revision_obj.approval_status != Status.PENDING:
                raise BaseExceptionMixin(
                    f"Revision is already {revision_obj.approval_status}.",
                    status_code=409,
                )

            tutor = None
            if revision_obj.tutor_id:
                tutor = await session.get(Tutor, revision_obj.tutor_id)

            if not tutor:
                created_tutor = await self.create(
                    data=TutorModel(
                        academic_program=revision_obj.academic_program,
                        bio=revision_obj.bio,
                        phone=revision_obj.phone,
                        teaching_style=revision_obj.teaching_style,
                        is_visible=revision_obj.is_visible,
                        approval_status=Status.ACCEPTED,
                        accepting_requests=revision_obj.accepting_requests,
                        tags=revision_obj.tags,
                    ),
                    session=session,
                )
                tutor = created_tutor["data"]
                revision_obj.tutor_id = tutor.id

                if revision_obj.user_id:
                    user = await session.get(User, revision_obj.user_id)
                    if user:
                        user.has_registered = True
                        user.is_verified = True
                        if revision_obj.full_name is not None:
                            user.full_name = revision_obj.full_name

                    association_query = select(UserRoleAssociation).join(
                        Role,
                        UserRoleAssociation.role_id == Role.id,
                    ).where(
                        UserRoleAssociation.user_id == revision_obj.user_id,
                        func.lower(Role.slug) == "tutor",
                    )
                    association = (await session.execute(association_query)).scalars().first()
                    if association:
                        association.tutor_id = tutor.id

            if revision_obj.full_name is not None:
                user_id_for_tutor = revision_obj.user_id
                if not user_id_for_tutor:
                    user_id_for_tutor = await UserRoleAssociationRepository().get_user_id_by_tutor_id(
                        tutor.id, session=session
                    )
                if user_id_for_tutor:
                    await UserRepository().update(
                        _id=user_id_for_tutor,
                        data=UpdateUserModel(full_name=revision_obj.full_name),
                        session=session,
                    )

            tutor.academic_program = revision_obj.academic_program
            tutor.bio = revision_obj.bio
            tutor.phone = revision_obj.phone
            tutor.teaching_style = revision_obj.teaching_style
            tutor.is_visible = revision_obj.is_visible
            tutor.accepting_requests = revision_obj.accepting_requests
            tutor.tags = revision_obj.tags
            tutor.approval_status = Status.ACCEPTED

            revision_obj.approval_status = Status.ACCEPTED

            tutor_account_user_id = revision_obj.user_id
            if tutor_account_user_id is None and tutor is not None:
                tutor_account_user_id = (
                    await UserRoleAssociationRepository().get_user_id_by_tutor_id(
                        tutor.id, session=session
                    )
                )
            if tutor_account_user_id is not None:
                await NotificationRepository().create_for_user(
                    user_id=tutor_account_user_id,
                    notification_type="TUTOR_PROFILE_APPROVED",
                    title="Tutor profile approved",
                    message="Your tutor profile revision was approved.",
                    data={
                        "revision_id": str(revision_obj.id),
                        "tutor_id": str(tutor.id) if tutor else None,
                    },
                    session=session,
                )

            # Build a minimal response dict here to avoid triggering lazy-loads
            revision_data = {
                "id": revision_obj.id,
                "tutor_id": getattr(revision_obj, "tutor_id", None) or (tutor.id if tutor else None),
                "full_name": getattr(revision_obj, "full_name", None),
                "academic_program": getattr(revision_obj, "academic_program", None),
                "bio": getattr(revision_obj, "bio", None),
                "phone": getattr(revision_obj, "phone", None),
                "teaching_style": getattr(revision_obj, "teaching_style", None),
                "is_visible": getattr(revision_obj, "is_visible", None),
                "approval_status": revision_obj.approval_status,
                "rejection_reason": getattr(revision_obj, "rejection_reason", None),
                "revision_type": getattr(revision_obj, "revision_type", None),
                "user_id": getattr(revision_obj, "user_id", None),
            }

            await session.commit()

            return {
                "success": True,
                "message": "Tutor revision approved.",
                "data": revision_data,
            }

    async def reject_tutor_revision(self, revision_id: UUID, rejection_reason: str):
        async with get_session() as session:
            query = select(TutorRevision).where(TutorRevision.id == revision_id).options(
                joinedload(TutorRevision.tutor_revision_tutor)
                .joinedload(Tutor.tutor_ura)
                .joinedload(UserRoleAssociation.ura_user)
            )
            result = await session.execute(query)
            revision_obj = result.scalars().first()
            if not revision_obj:
                raise NotFoundError(message="Revision not found.", status_code=404)
            if revision_obj.approval_status != Status.PENDING:
                raise BaseExceptionMixin(
                    f"Revision is already {revision_obj.approval_status}.",
                    status_code=409,
                )

            revision_obj.approval_status = Status.REJECTED
            revision_obj.rejection_reason = rejection_reason

            tutor_account_user_id = revision_obj.user_id
            if tutor_account_user_id is None and revision_obj.tutor_id is not None:
                tutor_account_user_id = (
                    await UserRoleAssociationRepository().get_user_id_by_tutor_id(
                        revision_obj.tutor_id, session=session
                    )
                )
            if tutor_account_user_id is not None:
                await NotificationRepository().create_for_user(
                    user_id=tutor_account_user_id,
                    notification_type="TUTOR_PROFILE_REJECTED",
                    title="Tutor profile rejected",
                    message="Your tutor profile revision was rejected.",
                    data={
                        "revision_id": str(revision_obj.id),
                        "rejection_reason": rejection_reason,
                    },
                    session=session,
                )

            # Build a minimal response dict to avoid lazy-loading expired attributes
            revision_data = {
                "id": revision_obj.id,
                "tutor_id": getattr(revision_obj, "tutor_id", None),
                "full_name": getattr(revision_obj, "full_name", None),
                "academic_program": getattr(revision_obj, "academic_program", None),
                "bio": getattr(revision_obj, "bio", None),
                "phone": getattr(revision_obj, "phone", None),
                "teaching_style": getattr(revision_obj, "teaching_style", None),
                "is_visible": getattr(revision_obj, "is_visible", None),
                "approval_status": revision_obj.approval_status,
                "rejection_reason": revision_obj.rejection_reason,
                "revision_type": getattr(revision_obj, "revision_type", None),
                "user_id": getattr(revision_obj, "user_id", None),
            }

            await session.commit()

            return {
                "success": True,
                "message": "Tutor revision rejected.",
                "data": revision_data,
            }

    async def get_tutor_revisions(
        self,
        tutor_id: UUID,
        approval_status: Status | None = None,
        limit: int = 100,
        offset: int = 0,
    ):
        async with get_session() as session:
            conditions = [TutorRevision.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                conditions.append(TutorRevision.approval_status == str(approval_status).upper())

            query = (
                select(TutorRevision)
                .where(*conditions)
                .order_by(desc(TutorRevision.created_at))
                .limit(limit)
                .offset(offset)
                .options(
                    joinedload(TutorRevision.tutor_revision_tutor)
                    .joinedload(Tutor.tutor_ura)
                    .joinedload(UserRoleAssociation.ura_user),
                    joinedload(TutorRevision.tutor_revision_user),
                )
            )
            result = await session.execute(query)
            revisions = result.scalars().all()
            count_conditions = [TutorRevision.tutor_id == tutor_id]
            if approval_status and str(approval_status).upper() != "ALL":
                count_conditions.append(TutorRevision.approval_status == str(approval_status).upper())
            count_query = select(TutorRevision).where(*count_conditions)
            count_result = await session.execute(count_query)
            total = len(count_result.scalars().all())
            return {
                "success": True,
                "message": "Tutor revisions fetched.",
                "data": revisions,
                "metadata": {"total": total, "limit": limit, "offset": offset},
            }

    async def _get_pending_revision_for_tutor(
        self,
        tutor_id: UUID,
        session: AsyncSession,
    ) -> Optional[TutorRevision]:
        query = (
            select(TutorRevision)
            .where(
                TutorRevision.tutor_id == tutor_id,
                TutorRevision.approval_status == Status.PENDING,
            )
        )
        result = await session.execute(query)
        return result.scalars().first()

    def _revision_to_dict(self, revision_obj: TutorRevision) -> dict:
        state = inspect(revision_obj)
        loaded_values = state.dict or {}
        revision_data = {
            column.key: loaded_values.get(column.key)
            for column in revision_obj.__table__.columns
        }

        user = None
        user_state = state.attrs.tutor_revision_user
        if user_state.loaded_value is not None:
            ura_user = user_state.value
            if ura_user:
                user = {
                    "full_name": ura_user.full_name,
                    "email": ura_user.email,
                    "id": ura_user.id,
                }
        else:
            tutor_state = state.attrs.tutor_revision_tutor
            if tutor_state.loaded_value is not None:
                tutor_relation = tutor_state.value
                if tutor_relation and tutor_relation.tutor_ura:
                    ura_user = tutor_relation.tutor_ura[0].ura_user if tutor_relation.tutor_ura else None
                    if ura_user:
                        user = {
                            "full_name": ura_user.full_name,
                            "email": ura_user.email,
                            "id": ura_user.id,
                        }
        revision_data["user"] = user
        return revision_data

    async def update_profile_picture(
        self,
        tutor_id: UUID,
        profile_picture_url: Optional[str],
        session: AsyncSession = None,
    ) -> Optional[Tutor]:
        """Update tutor's profile picture URL"""
        tutor = (await self.get(_id=tutor_id, session=session))["data"]
        if tutor:
            tutor.profile_picture_url = profile_picture_url
            await self.update(_id=tutor.id, data=tutor, session=session)
        return tutor

    async def update_cover_picture(
        self,
        tutor_id: UUID,
        cover_picture_url: Optional[str],
        session: AsyncSession = None,
    ) -> Optional[Tutor]:
        """Update tutor's cover picture URL"""
        tutor = (await self.get(_id=tutor_id, session=session))["data"]
        if tutor:
            tutor.cover_picture_url = cover_picture_url
            await self.update(_id=tutor.id, data=tutor, session=session)
        return tutor

    async def get_tutor_with_pictures(
        self, tutor_id: UUID, session: AsyncSession = None
    ) -> Tuple[Optional[Tutor], Optional[str], Optional[str]]:
        """Get tutor and their picture URLs"""
        tutor = (await self.get(_id=tutor_id, session=session))["data"]
        if tutor:
            return tutor, tutor.profile_picture_url, tutor.cover_picture_url
        return None, None, None

    async def delete_profile_picture_url(
        self, tutor_id: UUID, session: AsyncSession = None
    ) -> bool:
        """Delete profile picture URL from database"""
        tutor = (await self.get(_id=tutor_id, session=session))["data"]
        if tutor:
            tutor.profile_picture_url = None
            await self.update(_id=tutor.id, data=tutor, session=session)
            return True
        return False

    async def delete_cover_picture_url(
        self, tutor_id: UUID, session: AsyncSession = None
    ) -> bool:
        """Delete cover picture URL from database"""
        tutor = (await self.get(_id=tutor_id, session=session))["data"]
        if tutor:
            tutor.cover_picture_url = None
            await self.update(_id=tutor.id, data=tutor, session=session)
            return True
        return False

    async def update_tutor(
        self,
        tutor_id: UUID,
        update_data: UpdateTutorInputValidator,
    ):
        async with get_session() as session:
            tutor = (await self.get(_id=tutor_id, session=session))["data"]
            if not tutor:
                return None

            full_name = None
            if update_data.full_name is not None:
                full_name = update_data.full_name

            revision = await self.create_tutor_revision(
                tutor_id=tutor.id,
                full_name=full_name,
                update_data=update_data,
                session=session,
            )
            return revision

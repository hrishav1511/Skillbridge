import pytest
from contextlib import asynccontextmanager
from datetime import date, time
from uuid import uuid4
from unittest.mock import AsyncMock

from sqlalchemy import select

import skillbridge.api.repositories.service as service_repo_module
import skillbridge.api.repositories.tutor as tutor_repo_module
from skillbridge.api.repositories.service import ServiceRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.repositories.user_role_association import UserRoleAssociationRepository
from skillbridge.api.repositories.user import UserRepository
from skillbridge.api.validators.tutor import (
    CreateTutorInputValidator,
    UpdateTutorInputValidator,
)
from skillbridge.api.validators.user import UserRegisterInputValidator
from skillbridge.api.validators.service import RevisionType
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.notifications import Notification
from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.tutor_revisions import TutorRevision
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.utils.renderer import Status


async def _override_get_session(session):
    @asynccontextmanager
    async def get_session_override():
        yield session

    return get_session_override


async def _create_role(session, slug: str, title: str | None = None):
    role = Role(slug=slug, title=title or slug.title(), description=f"{slug} role")
    session.add(role)
    await session.flush()
    await session.refresh(role)
    return role


async def _create_user(session, email: str, full_name: str = "Test User"):
    user = User(
        full_name=full_name,
        email=email,
        password="password",
        has_registered=True,
        is_verified=True,
    )
    session.add(user)
    await session.flush()
    await session.refresh(user)
    return user


async def _create_tutor(session, approval_status: str = Status.ACCEPTED):
    tutor = Tutor(
        academic_program="Computer Science",
        bio="Experienced tutor.",
        phone="1234567890",
        teaching_style="Interactive",
        is_visible=True,
        approval_status=approval_status,
        accepting_requests=True,
    )
    session.add(tutor)
    await session.flush()
    await session.refresh(tutor)
    return tutor


async def _create_user_role_association(
    session,
    user_id,
    role_id,
    tutor_id=None,
):
    association = UserRoleAssociation(
        user_id=user_id,
        role_id=role_id,
        tutor_id=tutor_id,
    )
    session.add(association)
    await session.flush()
    await session.refresh(association)
    return association


@pytest.mark.asyncio
async def test_create_tutor_profile_creates_pending_revision(test_session, monkeypatch):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(tutor_repo_module, "get_session", get_session_override)

    tutor_input = CreateTutorInputValidator(
        academic_program="Mathematics",
        bio="I love teaching math.",
        phone="555-1234",
        teaching_style="Hands-on",
        is_visible=False,
        accepting_requests=False,
    )

    response = await TutorRepository().create_tutor_profile(tutor_input=tutor_input)

    assert response["success"] is True
    assert response["data"].id is not None
    assert response["data"].academic_program == "Mathematics"

    revision_result = await test_session.execute(
        select(TutorRevision).where(TutorRevision.tutor_id == response["data"].id)
    )
    revision = revision_result.scalars().first()

    assert revision is not None
    assert revision.revision_type == RevisionType.CREATE
    assert revision.approval_status == Status.PENDING
    assert revision.academic_program == "Mathematics"


@pytest.mark.asyncio
async def test_tutor_registration_request_creates_pending_revision_and_approves_user(test_session, monkeypatch):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(tutor_repo_module, "get_session", get_session_override)

    tutor_role = await _create_role(test_session, slug="TUTOR")
    admin_role = await _create_role(test_session, slug="ADMIN")
    tutor_user = User(
        full_name="Tutor Pending",
        email="pending-tutor@hs-fulda.de",
        password="password",
        has_registered=False,
        is_verified=False,
    )
    test_session.add(tutor_user)
    await test_session.flush()
    await test_session.refresh(tutor_user)

    register_data = UserRegisterInputValidator(
        full_name="Tutor Pending",
        email="pending-tutor@hs-fulda.de",
        phone="555-0000",
        password="Password123!",
        confirm_password="Password123!",
        role_id=tutor_role.id,
        academic_program="Engineering",
        bio="Pending approval tutor.",
        teaching_style="Interactive",
        is_visible=True,
        accepting_requests=True,
    )

    revision = await TutorRepository().create_tutor_registration_request(
        register_data=register_data,
        user_id=tutor_user.id,
        session=test_session,
    )
    await test_session.commit()

    assert revision["success"] is True
    assert revision["data"].tutor_id is None
    assert revision["data"].user_id == tutor_user.id
    assert revision["data"].approval_status == Status.PENDING

    admin_user = await _create_user(test_session, email="admin@example.com", full_name="Admin")
    await _create_user_role_association(
        test_session,
        user_id=admin_user.id,
        role_id=admin_role.id,
    )
    await _create_user_role_association(
        test_session,
        user_id=tutor_user.id,
        role_id=tutor_role.id,
        tutor_id=None,
    )
    await test_session.commit()

    approval_result = await TutorRepository().approve_tutor_revision(
        revision_id=revision["data"].id,
        user_id=admin_user.id,
    )

    assert approval_result["success"] is True
    assert approval_result["data"]["approval_status"] == Status.ACCEPTED

    updated_user = await test_session.get(User, tutor_user.id)
    assert updated_user.has_registered is True
    assert updated_user.is_verified is True

    association_result = await test_session.execute(
        select(UserRoleAssociation).where(
            UserRoleAssociation.user_id == tutor_user.id,
            UserRoleAssociation.role_id == tutor_role.id,
        )
    )
    association = association_result.scalars().first()
    assert association is not None
    assert association.tutor_id == approval_result["data"]["tutor_id"]
    assert (await test_session.execute(
        select(Notification).where(
            Notification.user_id == tutor_user.id,
            Notification.notification_type == "TUTOR_PROFILE_APPROVED",
        )
    )).scalar_one()


@pytest.mark.asyncio
async def test_update_tutor_creates_pending_revision_and_keeps_original(test_session, monkeypatch):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(tutor_repo_module, "get_session", get_session_override)

    tutor = await _create_tutor(test_session, approval_status=Status.ACCEPTED)
    await test_session.commit()

    update_input = UpdateTutorInputValidator(
        academic_program="Physics",
        bio="Advanced physics tutoring.",
    )

    revision_response = await TutorRepository().update_tutor(
        tutor_id=tutor.id,
        update_data=update_input,
    )

    assert revision_response is not None
    assert revision_response["success"] is True
    assert revision_response["data"].revision_type == RevisionType.UPDATE
    assert revision_response["data"].academic_program == "Physics"
    assert revision_response["data"].bio == "Advanced physics tutoring."
    assert revision_response["data"].approval_status == Status.PENDING

    refreshed_tutor = await test_session.get(Tutor, tutor.id)
    assert refreshed_tutor.academic_program == "Computer Science"
    assert refreshed_tutor.bio == "Experienced tutor."


@pytest.mark.asyncio
async def test_admin_can_approve_tutor_revision_updates_tutor(test_session, monkeypatch):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(tutor_repo_module, "get_session", get_session_override)

    admin_role = await _create_role(test_session, slug="ADMIN")
    tutor_role = await _create_role(test_session, slug="TUTOR")
    admin_user = await _create_user(test_session, email="admin@example.com", full_name="Admin User")
    tutor_user = await _create_user(test_session, email="tutor@example.com", full_name="Tutor User")

    tutor = await _create_tutor(test_session, approval_status=Status.ACCEPTED)
    await _create_user_role_association(
        test_session,
        user_id=admin_user.id,
        role_id=admin_role.id,
    )
    await _create_user_role_association(
        test_session,
        user_id=tutor_user.id,
        role_id=tutor_role.id,
        tutor_id=tutor.id,
    )
    await test_session.commit()

    update_input = UpdateTutorInputValidator(
        academic_program="Data Science",
    )
    revision_response = await TutorRepository().update_tutor(
        tutor_id=tutor.id,
        update_data=update_input,
    )

    revision_id = revision_response["data"].id
    approval_result = await TutorRepository().approve_tutor_revision(
        revision_id=revision_id,
        user_id=admin_user.id,
    )

    assert approval_result["success"] is True
    assert approval_result["data"]["approval_status"] == Status.ACCEPTED
    assert approval_result["data"]["revision_type"] == RevisionType.UPDATE

    refreshed_tutor = await test_session.get(Tutor, tutor.id)
    assert refreshed_tutor.academic_program == "Data Science"
    assert refreshed_tutor.approval_status == Status.ACCEPTED
    assert (await test_session.execute(
        select(Notification).where(
            Notification.user_id == tutor_user.id,
            Notification.notification_type == "TUTOR_PROFILE_APPROVED",
        )
    )).scalar_one()


@pytest.mark.asyncio
async def test_admin_can_reject_tutor_revision(test_session, monkeypatch):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(tutor_repo_module, "get_session", get_session_override)

    admin_role = await _create_role(test_session, slug="ADMIN")
    tutor_role = await _create_role(test_session, slug="TUTOR")
    admin_user = await _create_user(test_session, email="admin@example.com", full_name="Admin User")
    tutor_user = await _create_user(test_session, email="tutor@example.com", full_name="Tutor User")
    tutor = await _create_tutor(test_session, approval_status=Status.ACCEPTED)
    await _create_user_role_association(
        test_session,
        user_id=admin_user.id,
        role_id=admin_role.id,
    )
    await _create_user_role_association(
        test_session,
        user_id=tutor_user.id,
        role_id=tutor_role.id,
        tutor_id=tutor.id,
    )
    await test_session.commit()

    revision = TutorRevision(
        tutor_id=tutor.id,
        full_name=None,
        academic_program="Biology",
        bio="New bio.",
        phone="123-4567",
        teaching_style="Lecture",
        is_visible=True,
        approval_status=Status.PENDING,
        accepting_requests=True,
        rejection_reason=None,
        revision_type=RevisionType.UPDATE,
    )
    test_session.add(revision)
    await test_session.flush()
    await test_session.refresh(revision)
    await test_session.commit()

    reject_result = await TutorRepository().reject_tutor_revision(
        revision_id=revision.id,
        rejection_reason="Not a good fit.",
    )

    assert reject_result["success"] is True
    assert reject_result["data"]["approval_status"] == Status.REJECTED
    assert reject_result["data"]["rejection_reason"] == "Not a good fit."

    refreshed_revision = await test_session.get(TutorRevision, revision.id)
    assert refreshed_revision.approval_status == Status.REJECTED
    assert refreshed_revision.rejection_reason == "Not a good fit."
    assert (await test_session.execute(
        select(Notification).where(
            Notification.user_id == tutor_user.id,
            Notification.notification_type == "TUTOR_PROFILE_REJECTED",
        )
    )).scalar_one()


@pytest.mark.asyncio
async def test_admin_can_reject_pending_service_revision_without_lazy_load_error(
    test_session, monkeypatch
):
    get_session_override = await _override_get_session(test_session)
    monkeypatch.setattr(service_repo_module, "get_session", get_session_override)
    monkeypatch.setattr(service_repo_module.manager, "send_to_user", AsyncMock(return_value=False))

    admin_role = await _create_role(test_session, slug="ADMIN")
    tutor_role = await _create_role(test_session, slug="TUTOR")
    admin_user = await _create_user(test_session, email="admin@example.com", full_name="Admin User")
    tutor_user = await _create_user(test_session, email="tutor@example.com", full_name="Tutor User")
    tutor = await _create_tutor(test_session, approval_status=Status.ACCEPTED)
    await _create_user_role_association(
        test_session,
        user_id=admin_user.id,
        role_id=admin_role.id,
    )
    await _create_user_role_association(
        test_session,
        user_id=tutor_user.id,
        role_id=tutor_role.id,
        tutor_id=tutor.id,
    )
    await test_session.commit()

    revision = ServiceRevision(
        tutor_id=tutor.id,
        service_name="Python 101",
        description="Beginner-friendly Python lessons",
        date=date.today(),
        time=time(9, 0),
        price=45,
        level="BEGINNER",
        joining_link="https://example.com/session",
        tags=["python", "beginner"],
        approval_status=Status.PENDING,
        revision_type=RevisionType.CREATE,
    )
    test_session.add(revision)
    await test_session.flush()
    await test_session.refresh(revision)
    await test_session.commit()

    result = await ServiceRepository().reject_revision(
        revision_id=revision.id,
        rejection_reason="Content does not match the course description.",
    )

    assert result["success"] is True
    assert result["data"]["approval_status"] == Status.REJECTED
    assert result["data"]["rejection_reason"] == "Content does not match the course description."

    refreshed_revision = await test_session.get(ServiceRevision, revision.id)
    assert refreshed_revision.approval_status == Status.REJECTED
    assert refreshed_revision.rejection_reason == "Content does not match the course description."

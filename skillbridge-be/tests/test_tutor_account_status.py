from contextlib import asynccontextmanager
from uuid import uuid4

import pytest
from skillbridge.api.repositories import tutor as tutor_repository
from skillbridge.api.repositories.auth.base import AuthService
from skillbridge.api.repositories.auth.login import LoginRepository
from skillbridge.api.repositories.tutor import TutorRepository
from skillbridge.api.filters.tutor import TutorSearchFilter
from skillbridge.api.validators.login import LoginInputValidator
from skillbridge.api.validators.tutor import TutorSearchValidator
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import NotRegisteredError

LOGIN_PASSWORD = "Passw0rd!x"


@pytest.fixture
def tutor_account_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(tutor_repository, "get_session", session_context)
    return test_session


async def _seed_tutor_account(session, status="ACTIVE"):
    role = Role(id=uuid4(), title="TUTOR", slug="tutor")
    user = User(
        id=uuid4(),
        full_name="Tutor User",
        email=f"tutor-{uuid4()}@example.com",
        password=AuthService().hash_password(LOGIN_PASSWORD),
        status=status,
        has_registered=True,
    )
    tutor = Tutor(id=uuid4(), academic_program="Computer Science")
    session.add_all([role, user, tutor])
    await session.flush()
    association = UserRoleAssociation(
        user_id=user.id,
        role_id=role.id,
        tutor_id=tutor.id,
    )
    session.add(association)
    await session.flush()
    return user, tutor


@pytest.mark.asyncio
async def test_admin_tutor_listing_includes_linked_user_status(tutor_account_session):
    user, tutor = await _seed_tutor_account(tutor_account_session, status="ACTIVE")

    result = await TutorRepository().get_admin_tutors()

    assert result["metadata"]["total"] == 1
    listed_tutor = result["data"][0]
    assert listed_tutor.id == tutor.id
    assert listed_tutor.tutor_ura[0].ura_user.status == "ACTIVE"
    assert listed_tutor.tutor_ura[0].ura_user.id == user.id


@pytest.mark.asyncio
async def test_admin_can_disable_and_reactivate_tutor_account(tutor_account_session):
    """Deactivation lands on the Tutor row, leaving the login account alone."""
    user, tutor = await _seed_tutor_account(tutor_account_session)

    disabled = await TutorRepository().set_account_status(tutor.id, "INACTIVE")
    assert disabled.id == tutor.id
    assert disabled.status == "INACTIVE"
    assert user.status == "ACTIVE", "deactivating a tutor must not disable their login"

    active = await TutorRepository().set_account_status(tutor.id, "ACTIVE")
    assert active.status == "ACTIVE"


@pytest.mark.asyncio
async def test_deactivated_tutor_can_still_log_in(tutor_account_session):
    """A deactivated tutor keeps access to their own account.

    "Removed from the marketplace" and "account disabled" are different states;
    only the latter may block authentication.
    """
    user, tutor = await _seed_tutor_account(tutor_account_session)
    await TutorRepository().set_account_status(tutor.id, "INACTIVE")
    role = (await tutor_account_session.execute(
        Role.__table__.select().where(Role.slug == "tutor")
    )).first()

    association = await LoginRepository().check_user_register_status(
        email=user.email,
        role_id=role.id,
        login_data=LoginInputValidator(
            email=user.email,
            password=LOGIN_PASSWORD,
            role_id=role.id,
        ),
        session=tutor_account_session,
    )
    assert association.user_id == user.id


@pytest.mark.asyncio
async def test_a_genuinely_disabled_account_still_cannot_login(tutor_account_session):
    """The User-level ban is the separate state, and it still blocks login."""
    user, _ = await _seed_tutor_account(tutor_account_session, status="INACTIVE")
    role = (await tutor_account_session.execute(
        Role.__table__.select().where(Role.slug == "tutor")
    )).first()

    with pytest.raises(NotRegisteredError) as error:
        await LoginRepository().check_user_register_status(
            email=user.email,
            role_id=role.id,
            login_data=LoginInputValidator(
                email=user.email,
                password=LOGIN_PASSWORD,
                role_id=role.id,
            ),
            session=tutor_account_session,
        )

    assert error.value.status_code == 403
    assert "temporarily disabled" in error.value.message


@pytest.mark.asyncio
async def test_tutor_can_hide_and_reactivate_profile(tutor_account_session):
    user, tutor = await _seed_tutor_account(tutor_account_session)

    hidden = await TutorRepository().update_visibility(tutor.id, user.id, False)
    assert hidden.is_visible is False

    active = await TutorRepository().update_visibility(tutor.id, user.id, True)
    assert active.is_visible is True


@pytest.mark.asyncio
async def test_tutor_can_pause_and_resume_availability(tutor_account_session):
    user, tutor = await _seed_tutor_account(tutor_account_session)

    paused = await TutorRepository().update_availability(tutor.id, user.id, False)
    assert paused.accepting_requests is False

    resumed = await TutorRepository().update_availability(tutor.id, user.id, True)
    assert resumed.accepting_requests is True


@pytest.mark.asyncio
async def test_public_tutor_filter_requires_visible_approved_profile():
    filter_instance = await TutorSearchFilter(
        TutorSearchValidator(public_only=True)
    )

    combined_filters = " ".join(str(item).lower() for item in filter_instance._filters)
    assert len(filter_instance._filters) == 4
    assert "is_visible" in combined_filters
    assert "approval_status" in combined_filters
    assert "tutors.status" in combined_filters
    assert "users.status" in combined_filters

from contextlib import asynccontextmanager
from datetime import date, time
from uuid import uuid4

import pytest

from skillbridge.api.repositories import favorite as favorite_repository
from skillbridge.api.repositories.favorite import FavoriteRepository
from skillbridge.database.models.sqlalchemy.services import Service, ServiceLevel
from skillbridge.database.models.sqlalchemy.student_favorite_services import StudentFavoriteService
from skillbridge.database.models.sqlalchemy.student_favorite_tutors import StudentFavoriteTutor
from skillbridge.database.models.sqlalchemy.tutors import Tutor


@pytest.fixture
def favorites_session(test_session, monkeypatch):
    @asynccontextmanager
    async def session_context():
        yield test_session

    monkeypatch.setattr(favorite_repository, "get_session", session_context)
    return test_session


@pytest.mark.asyncio
async def test_student_can_favorite_and_unfavorite_tutor(favorites_session):
    student_id = uuid4()
    tutor_id = uuid4()
    favorites_session.add(Tutor(id=tutor_id, academic_program="Computer Science"))
    await favorites_session.flush()

    repository = FavoriteRepository()
    assert await repository.set_tutor_favorite(student_id, tutor_id, True) is True
    assert await repository.get_tutor_ids(student_id) == {tutor_id}
    assert await repository.set_tutor_favorite(student_id, tutor_id, False) is False
    assert await repository.get_tutor_ids(student_id) == set()


@pytest.mark.asyncio
async def test_student_can_favorite_and_unfavorite_service(favorites_session):
    student_id = uuid4()
    service_id = uuid4()
    favorites_session.add(
        Service(
            id=service_id,
            tutor_id=uuid4(),
            service_name="Python",
            date=date.today(),
            time=time(12, 0),
            price=10,
            level=ServiceLevel.BEGINNER,
        )
    )
    await favorites_session.flush()

    repository = FavoriteRepository()
    assert await repository.set_service_favorite(student_id, service_id, True) is True
    assert await repository.get_service_ids(student_id) == {service_id}
    assert await repository.set_service_favorite(student_id, service_id, False) is False
    assert await repository.get_service_ids(student_id) == set()


@pytest.mark.asyncio
async def test_favorite_operations_are_idempotent(favorites_session):
    student_id = uuid4()
    tutor_id = uuid4()
    favorites_session.add(Tutor(id=tutor_id))
    await favorites_session.flush()

    repository = FavoriteRepository()
    await repository.set_tutor_favorite(student_id, tutor_id, True)
    await repository.set_tutor_favorite(student_id, tutor_id, True)

    result = await favorites_session.execute(
        StudentFavoriteTutor.__table__.select().where(
            StudentFavoriteTutor.student_id == student_id
        )
    )
    assert len(result.fetchall()) == 1

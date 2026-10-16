"""Seed helpers for tests that drive the real FastAPI app.

Each helper returns the persisted row so a test can assert against ids without
re-querying. Everything is deliberately explicit: these tests exist to pin down
visibility and authorization rules, so the state under test should be readable
from the test body.
"""

import uuid
from datetime import date, time, timedelta

from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User

PASSWORD = "Passw0rd!x"


async def seed_roles(session, slugs=("student", "tutor", "admin")):
    roles = {}
    for slug in slugs:
        role = Role(
            id=uuid.uuid4(),
            slug=slug,
            title=slug,
            description=slug,
            status="ACTIVE",
        )
        session.add(role)
        roles[slug] = role
    await session.flush()
    return roles


def make_user(session, email, *, full_name="Person", phone="+4915100000",
              status="ACTIVE"):
    user = User(
        id=uuid.uuid4(),
        full_name=full_name,
        email=email,
        phone=phone,
        status=status,
        has_registered=True,
        is_verified=True,
        password=TokenRepository.hash_password(PASSWORD),
    )
    session.add(user)
    return user


def make_tutor(session, *, is_visible=True, accepting_requests=True,
               approval_status="ACCEPTED", status="ACTIVE", phone="+4917500000",
               tags=None):
    tutor = Tutor(
        id=uuid.uuid4(),
        academic_program="CS",
        bio="bio",
        phone=phone,
        teaching_style="Interactive",
        is_visible=is_visible,
        approval_status=approval_status,
        accepting_requests=accepting_requests,
        tags=tags if tags is not None else ["Python"],
        status=status,
    )
    session.add(tutor)
    return tutor


def make_student(session, *, status="ACTIVE"):
    student = Student(id=uuid.uuid4(), status=status)
    session.add(student)
    return student


def link(session, user, role, *, tutor=None, student=None):
    association = UserRoleAssociation(
        id=uuid.uuid4(),
        user_id=user.id,
        role_id=role.id,
        tutor_id=tutor.id if tutor is not None else None,
        student_id=student.id if student is not None else None,
        status="ACTIVE",
    )
    session.add(association)
    return association


def make_service(session, tutor, *, name="Service", days_ahead=5, price=30,
                 level="BEGINNER", status="ACTIVE", tags=None):
    service = Service(
        id=uuid.uuid4(),
        tutor_id=tutor.id,
        service_name=name,
        description="d",
        date=date.today() + timedelta(days=days_ahead),
        time=time(10, 0),
        end_time=time(11, 0),
        price=price,
        level=level,
        tags=tags if tags is not None else ["Python"],
        status=status,
    )
    session.add(service)
    return service

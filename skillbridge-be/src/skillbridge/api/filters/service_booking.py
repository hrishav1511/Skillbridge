import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.validators.service import ServiceBookingSearchValidator
from skillbridge.database.models.sqlalchemy.service_bookings import ServiceBooking
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)


class ServiceBookingSearchFilter(SearchFilter):
    model = ServiceBooking
    _search_criteria: ServiceBookingSearchValidator


    count_queryset = select(func.count(ServiceBooking.id))
    queryset = (
        select(ServiceBooking)
        .options(
            joinedload(ServiceBooking.service_booking_service)
            .joinedload(Service.service_tutor)
            .joinedload(Tutor.tutor_ura)
            .joinedload(UserRoleAssociation.ura_user),
            joinedload(ServiceBooking.service_booking_student)
            .joinedload(Student.student_ura)
            .joinedload(UserRoleAssociation.ura_user),
            selectinload(ServiceBooking.booking_reschedule_proposals),
        )
    )
    registered_filters = [
        "service_booking_id",
        "service_id",
        "student_id",
        "tutor_id",
        "status",
    ]

    async def service_booking_id(self):
        self._filters.append(
            getattr(self.model, "id") == self._search_criteria.service_booking_id
        )

    async def service_id(self):
        self._filters.append(
            getattr(self.model, "service_id") == self._search_criteria.service_id
        )

    async def student_id(self):
        self._filters.append(
            getattr(self.model, "student_id") == self._search_criteria.student_id
        )

    async def tutor_id(self):
        self._filters.append(
            self.model.service_booking_service.has(
                Service.tutor_id == self._search_criteria.tutor_id
            )
        )

    async def status(self):
        # BookingStatus is a str-mixin enum whose str() is "BookingStatus.X",
        # so read .value; the criteria may also arrive as a plain string.
        status = self._search_criteria.status
        status = getattr(status, "value", status)
        self._filters.append(
            func.upper(getattr(self.model, "status")) == str(status).upper()
        )

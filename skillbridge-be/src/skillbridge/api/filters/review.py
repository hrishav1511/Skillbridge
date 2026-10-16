import re

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.schemas.review import ServiceReviewQueryCriteria, TutorReviewQueryCriteria
from skillbridge.database.models.sqlalchemy.service_reviews import ServiceReview
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.user_role_associations import UserRoleAssociation
from skillbridge.database.models.sqlalchemy.users import User


class TutorReviewSearchFilter(SearchFilter):
    model = TutorReview
    _search_criteria: TutorReviewQueryCriteria
    # eager-load the student -> user_role_association -> user chain
    queryset = (
        select(TutorReview).options(
            joinedload(TutorReview.tutor_review_student)
            .joinedload(Student.student_ura)
            .joinedload(UserRoleAssociation.ura_user)
        )
    )
    count_queryset = select(func.count(TutorReview.id))
    registered_filters = ["tutor_id", "student_id"]

    async def tutor_id(self):
        self._filters.append(getattr(self.model, "tutor_id") == self._search_criteria.tutor_id)

    async def student_id(self):
        self._filters.append(getattr(self.model, "student_id") == self._search_criteria.student_id)

    def query(self):
        _query = re.sub(r"[^a-zA-Z0-9@.\s]+", "", self._search_criteria.query.lower()).strip()
        if _query:
            self._filters.append(
                getattr(self.model, "comment").ilike(f"%{_query}%")
            )


class ServiceReviewSearchFilter(SearchFilter):
    model = ServiceReview
    _search_criteria: ServiceReviewQueryCriteria
    # eager-load the student -> user_role_association -> user chain
    queryset = (
        select(ServiceReview).options(
            joinedload(ServiceReview.service_review_student)
            .joinedload(Student.student_ura)
            .joinedload(UserRoleAssociation.ura_user)
        )
    )
    count_queryset = select(func.count(ServiceReview.id))
    registered_filters = ["service_id", "student_id"]

    async def service_id(self):
        self._filters.append(getattr(self.model, "service_id") == self._search_criteria.service_id)

    async def student_id(self):
        self._filters.append(getattr(self.model, "student_id") == self._search_criteria.student_id)

    def query(self):
        _query = re.sub(r"[^a-zA-Z0-9@.\s]+", "", self._search_criteria.query.lower()).strip()
        if _query:
            self._filters.append(
                getattr(self.model, "comment").ilike(f"%{_query}%")
            )

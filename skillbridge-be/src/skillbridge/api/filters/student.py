import re

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.validators.student import StudentSearchValidator
from skillbridge.database.models.sqlalchemy.students import Student
from skillbridge.database.models.sqlalchemy.users import User


class StudentSearchFilter(SearchFilter):
    """
    Class that defines all the search filters and executes them based
    on the attributes defined in search criteria to register new search filter.
    Define the filter as function and register it in registered_filters

    Returns:
        [type]: [description]
    """

    model = Student
    _search_criteria: StudentSearchValidator

    queryset = select(model)

    count_queryset = select(func.count(Student.id))

    registered_filters = ["student_id", "field_of_study", "enrolled_university"]

    async def student_id(self):
        self._filters.append(
            getattr(self.model, "id") == self._search_criteria.student_id
        )

    async def field_of_study(self):
        self._filters.append(
            getattr(self.model, "field_of_study").ilike(
                f"%{self._search_criteria.field_of_study}%"
            )
        )

    async def enrolled_university(self):
        self._filters.append(
            getattr(self.model, "enrolled_university").ilike(
                f"%{self._search_criteria.enrolled_university}%"
            )
        )

    def query(self):
        _query = re.sub(
            r"[^a-zA-Z0-9@.\s]+", "", self._search_criteria.query.lower()
        ).strip()
        self._filters.append(
            or_(
                self.model.tutor_user.has(
                    getattr(User, "full_name").ilike(f"%{_query}%")
                ),
                self.model.tutor_user.has(getattr(User, "email").ilike(f"%{_query}%")),
                self.model.tutor_user.has(getattr(User, "phone").ilike(f"%{_query}%")),
                getattr(self.model, "academic_program").ilike(f"%{_query}%"),
                getattr(self.model, "teaching_style").ilike(f"%{_query}%"),
            )
        )

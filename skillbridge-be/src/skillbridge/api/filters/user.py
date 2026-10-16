import re
from functools import reduce

from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.validators.user import UserSearchValidator
from skillbridge.database.models.sqlalchemy.users import User


class UserSearchFilter(SearchFilter):
    """
    Class that defines all the search filters and executes them based
    on the attributes defined in search criteria to register new search filter.
    Define the filter as function and register it in registered_filters

    Returns:
        [type]: [description]
    """

    model = User
    _search_criteria: UserSearchValidator

    queryset = select(User)

    count_queryset = select(func.count(User.id))

    registered_filters = [
        "user_id",
        "email",
        "name",
        "email_or_phone",
    ]

    async def user_id(self):
        self._filters.append(getattr(self.model, "id") == self._search_criteria.user_id)

    async def email(self):
        self._filters.append(
            getattr(self.model, "email").like(f"%{self._search_criteria.email}%"),
        )

    async def name(self):
        self._filters.append(
            getattr(self.model, "name").like(f"%{self._search_criteria.name}%"),
        )

    async def email_or_phone(self):
        self._filters.append(
            getattr(self.model, "email") == f"{self._search_criteria.email_or_phone}",
        )
        self._filters.append(
            getattr(self.model, "phone") == f"{self._search_criteria.email_or_phone}",
        ),

    async def get_filters(self):
        if self._filters:
            expr = reduce(or_, self._filters)
            return expr

    def query(self):
        _query = re.sub(
            r"[^a-zA-Z0-9@.\s]+", "", self._search_criteria.query.lower()
        ).strip()
        self._filters.append(
            or_(
                getattr(self.model, "name").ilike(f"%{_query}%"),
                getattr(self.model, "email").ilike(f"%{_query}%"),
                getattr(self.model, "phone").ilike(f"%{_query}%"),
            )
        )

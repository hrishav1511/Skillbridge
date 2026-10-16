from sqlalchemy import func, select

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.validators.role import RoleSearchValidator
from skillbridge.database.models.sqlalchemy.roles import Role


class RoleSearchFilter(SearchFilter):
    """
    Class that defines all the search filters and executes them based
    on the attributes defined in search criteria to register new search filter.
    Define the filter as function and register it in registered_filters

    Returns:
        [type]: [description]
    """

    model = Role
    _search_criteria: RoleSearchValidator

    # queryset = select(Role).options(
    #     joinedload(Role.notarization_detail, innerjoin=False).options(
    #         joinedload(Role.notarization_document, innerjoin=False),
    #     ),
    # )
    count_queryset = select(func.count(Role.id))

    registered_filters = ["role_id"]

    async def role_id(self):
        self._filters.append(getattr(self.model, "id") == self._search_criteria.role_id)

    # async def get_queryset(self) -> list[BinaryExpression]:
    #     notarization_query = []
    #     notarization_query.append(Notarization.id.in_([1, 2]))
    #     return notarization_query

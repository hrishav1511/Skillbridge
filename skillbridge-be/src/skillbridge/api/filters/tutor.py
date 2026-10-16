import re

from sqlalchemy import String, case, cast, func, or_, select
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.validators.tutor import TutorSearchValidator
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.database.models.sqlalchemy.tutor_reviews import TutorReview
from skillbridge.database.models.sqlalchemy.services import Service


class TutorSearchFilter(SearchFilter):
    """
    Class that defines all the search filters and executes them based
    on the attributes defined in search criteria to register new search filter.
    Define the filter as function and register it in registered_filters

    Returns:
        [type]: [description]
    """

    model = Tutor
    _search_criteria: TutorSearchValidator

    queryset = select(model).options(
        joinedload(Tutor.tutor_ura).joinedload(UserRoleAssociation.ura_user)
    )

    count_queryset = (
        select(func.count(Tutor.id))
        # .join(model.tutor_profile_utpa, isouter=True)
        # .join(model.tutor_user, isouter=True)
    )

    registered_filters = [
        "tutor_id",
        "academic_program",
        "tag",
        "teaching_style",
        "approval_status",
        "public_only",
    ]

    async def tutor_id(self):
        self._filters.append(
            getattr(self.model, "id") == self._search_criteria.tutor_id
        )

    async def academic_program(self):
        self._filters.append(
            getattr(self.model, "academic_program").ilike(
                f"%{self._search_criteria.academic_program}%"
            )
        )

    async def tag(self):
        """Match a single subject tag.

        ``tags`` is a JSON column, so this matches against its serialised form.
        The quotes are included so "Java" cannot match "JavaScript".
        """
        tag = str(self._search_criteria.tag).strip()
        self._filters.append(
            cast(getattr(self.model, "tags"), String).ilike(f'%"{tag}"%')
        )

    async def teaching_style(self):
        self._filters.append(
            getattr(self.model, "teaching_style").ilike(
                f"%{self._search_criteria.teaching_style}%"
            )
        )

    async def approval_status(self):
        approval_status = self._search_criteria.approval_status
        if approval_status and str(approval_status).upper() != "ALL":
            self._filters.append(
                getattr(self.model, "approval_status") == str(approval_status).upper()
            )

    async def public_only(self):
        self._filters.extend(
            [
                self.model.is_visible.is_(True),
                func.upper(self.model.approval_status).in_(("ACCEPTED", "APPROVED")),
                func.upper(self.model.status) == "ACTIVE",
                self.model.tutor_ura.any(
                    UserRoleAssociation.ura_user.has(func.upper(User.status) == "ACTIVE")
                ),
            ]
        )

    def get_sorting_orders(self):
        sort_value = (self._search_criteria.sort or "newest").lower()
        rating = (
            select(func.avg(TutorReview.rating))
            .where(TutorReview.tutor_id == self.model.id)
            .correlate(self.model)
            .scalar_subquery()
        )
        availability = case((self.model.accepting_requests.is_(True), 1), else_=0)
        if sort_value in {"rating:desc", "rating_desc", "highest_rating"}:
            return [
                case((rating.is_(None), 1), else_=0).asc(),
                rating.desc(),
                self.model.id.asc(),
            ]
        if sort_value in {"rating:asc", "rating_asc", "lowest_rating"}:
            # Unrated tutors sort last in both directions; "lowest rated"
            # should surface poor ratings, not an absence of them.
            return [
                case((rating.is_(None), 1), else_=0).asc(),
                rating.asc(),
                self.model.id.asc(),
            ]
        if sort_value in {"availability", "relevance"}:
            return [availability.desc(), self.model.created_at.desc(), self.model.id.asc()]
        if sort_value in {"newest", "newest:desc", "created_at:desc"}:
            return [self.model.created_at.desc(), self.model.id.asc()]
        return super().get_sorting_orders()

    def query(self):
        # If a free-text `query` is provided, sanitize and apply OR filters.
        raw_query = getattr(self._search_criteria, "query", None) or ""
        _query = raw_query.lower().strip()
        if _query:
            self._filters.append(
                or_(
                    self.model.tutor_ura.any(
                        UserRoleAssociation.ura_user.has(
                            getattr(User, "full_name").ilike(f"%{_query}%")
                        )
                    ),
                    self.model.tutor_ura.any(
                        UserRoleAssociation.ura_user.has(
                            getattr(User, "email").ilike(f"%{_query}%")
                        )
                    ),
                    self.model.tutor_ura.any(
                        UserRoleAssociation.ura_user.has(
                            getattr(User, "phone").ilike(f"%{_query}%")
                        )
                    ),
                    getattr(self.model, "academic_program").ilike(f"%{_query}%"),
                    getattr(self.model, "bio").ilike(f"%{_query}%"),
                    getattr(self.model, "teaching_style").ilike(f"%{_query}%"),
                    cast(self.model.tags, String).ilike(f"%{_query}%"),
                    self.model.tutor_service.any(
                        or_(
                            Service.service_name.ilike(f"%{_query}%"),
                            cast(Service.tags, String).ilike(f"%{_query}%"),
                        )
                    ),
                )
            )

        # If an explicit `name` parameter is provided, filter by the associated user's full_name.
        name_q = getattr(self._search_criteria, "name", None)
        if name_q:
            name_clean = re.sub(r"[^a-zA-Z0-9@.\s]+", "", name_q.lower()).strip()
            if name_clean:
                self._filters.append(
                    self.model.tutor_ura.any(
                        UserRoleAssociation.ura_user.has(
                            getattr(User, "full_name").ilike(f"%{name_clean}%")
                        )
                    )
                )

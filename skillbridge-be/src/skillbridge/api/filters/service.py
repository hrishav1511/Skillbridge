import re
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import String, and_, case, cast, func, or_, select
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.base import SearchFilter
from skillbridge.api.schemas.service import ServiceRevisionQueryCriteria
from skillbridge.api.validators.service import ServiceSearchValidator
from skillbridge.api.validators.service import ServiceScheduleStatus
from skillbridge.config import settings
from skillbridge.database.models.sqlalchemy.service_revisions import ServiceRevision
from skillbridge.database.models.sqlalchemy.services import Service
from skillbridge.database.models.sqlalchemy.service_reviews import ServiceReview
from skillbridge.database.models.sqlalchemy.tutors import Tutor
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User


class ServiceSearchFilter(SearchFilter):
    model = Service
    _search_criteria: ServiceSearchValidator

    queryset = select(Service).options(
        joinedload(Service.service_tutor)
        .joinedload(Tutor.tutor_ura)
        .joinedload(UserRoleAssociation.ura_user)
    )

    count_queryset = select(func.count(Service.id))
    registered_filters = [
        "service_id",
        "service_name",
        "tutor_name",
        "tutor_id",
        "schedule_status",
        "public_only",
        "min_price",
        "max_price",
        "academic_program",
    ]

    async def service_id(self):
        self._filters.append(
            getattr(self.model, "id") == self._search_criteria.service_id
        )

    async def service_name(self):
        self._filters.append(
            getattr(self.model, "service_name").ilike(
                f"%{self._search_criteria.service_name}%"
            )
        )

    async def min_price(self):
        self._filters.append(self.model.price >= self._search_criteria.min_price)

    async def max_price(self):
        self._filters.append(self.model.price <= self._search_criteria.max_price)

    def get_sorting_orders(self):
        sort_value = (self._search_criteria.sort or "newest").lower()
        rating = (
            select(func.avg(ServiceReview.rating))
            .where(ServiceReview.service_id == self.model.id)
            .correlate(self.model)
            .scalar_subquery()
        )
        schedule_priority = case(
            (self.model.date > func.current_date(), 2),
            (self.model.end_time.is_not(None), 1),
            else_=0,
        )
        if sort_value in {"price:asc", "price_asc", "lowest_price"}:
            return [self.model.price.asc(), self.model.id.asc()]
        if sort_value in {"price:desc", "price_desc", "highest_price"}:
            return [self.model.price.desc(), self.model.id.asc()]
        if sort_value in {"rating:desc", "rating_desc", "highest_rating"}:
            return [
                case((rating.is_(None), 1), else_=0).asc(),
                rating.desc(),
                self.model.id.asc(),
            ]
        if sort_value in {"rating:asc", "rating_asc", "lowest_rating"}:
            # Unrated services sort last either way, as for tutors.
            return [
                case((rating.is_(None), 1), else_=0).asc(),
                rating.asc(),
                self.model.id.asc(),
            ]
        if sort_value in {"date:asc", "date_asc", "earliest_session"}:
            # Order by the whole service start, so two services on one day
            # come back in the order they actually run.
            return [self.model.date.asc(), self.model.time.asc(), self.model.id.asc()]
        if sort_value in {"date:desc", "date_desc", "latest_session"}:
            return [self.model.date.desc(), self.model.time.desc(), self.model.id.asc()]
        if sort_value in {"availability", "relevance"}:
            return [schedule_priority.desc(), self.model.created_at.desc(), self.model.id.asc()]
        if sort_value in {"newest", "newest:desc", "created_at:desc"}:
            return [self.model.created_at.desc(), self.model.id.asc()]
        return super().get_sorting_orders()

    async def tutor_id(self):
        self._filters.append(
            getattr(self.model, "tutor_id") == self._search_criteria.tutor_id
        )

    async def academic_program(self):
        # Matches the tutor-list filter: partial and case-insensitive.
        self._filters.append(
            self.model.service_tutor.has(
                Tutor.academic_program.ilike(
                    f"%{self._search_criteria.academic_program}%"
                )
            )
        )

    async def tutor_name(self):
        self._filters.append(
            self.model.service_tutor.has(
                Tutor.tutor_ura.any(
                    UserRoleAssociation.ura_user.has(
                        getattr(User, "full_name").ilike(
                            f"%{self._search_criteria.tutor_name}%"
                        )
                    )
                )
            )
        )

    async def schedule_status(self):
        now = datetime.now(ZoneInfo(settings.SERVICE_TIMEZONE))
        today = now.date()
        current_time = now.time()
        start_has_passed = or_(
            self.model.date < today,
            and_(self.model.date == today, self.model.time <= current_time),
        )
        start_is_future = or_(
            self.model.date > today,
            and_(self.model.date == today, self.model.time > current_time),
        )
        end_time = func.coalesce(self.model.end_time, self.model.time)
        end_has_passed = or_(
            self.model.date < today,
            and_(self.model.date == today, end_time <= current_time),
        )
        end_is_future = or_(
            self.model.date > today,
            and_(self.model.date == today, end_time > current_time),
        )

        schedule_status = self._search_criteria.schedule_status
        if schedule_status == ServiceScheduleStatus.UPCOMING:
            self._filters.append(start_is_future)
        elif schedule_status == ServiceScheduleStatus.RUNNING:
            self._filters.append(and_(start_has_passed, end_is_future))
        elif schedule_status == ServiceScheduleStatus.COMPLETED:
            self._filters.append(end_has_passed)

    async def public_only(self):
        self._filters.extend(
            [
                func.upper(self.model.status) == "ACTIVE",
                self.model.service_tutor.has(
                    and_(
                        Tutor.is_visible.is_(True),
                        Tutor.accepting_requests.is_(True),
                        func.upper(Tutor.status) == "ACTIVE",
                        func.upper(Tutor.approval_status).in_(("ACCEPTED", "APPROVED")),
                        Tutor.tutor_ura.any(
                            UserRoleAssociation.ura_user.has(func.upper(User.status) == "ACTIVE")
                        ),
                    )
                ),
            ]
        )

    # async def approval_status(self):
    #     approval_status = self._search_criteria.approval_status
    #     if approval_status and str(approval_status).upper() != "ALL":
    #         self._filters.append(
    #             getattr(self.model, "approval_status")
    #             == str(approval_status).upper()
    #         )

    def query(self):
        _query = self._search_criteria.query.lower().strip()
        if _query:
            self._filters.append(
                or_(
                    getattr(self.model, "service_name").ilike(f"%{_query}%"),
                    getattr(self.model, "description").ilike(f"%{_query}%"),
                    cast(self.model.tags, String).ilike(f"%{_query}%"),
                    self.model.service_tutor.has(
                        Tutor.tutor_ura.any(
                            UserRoleAssociation.ura_user.has(
                                getattr(User, "full_name").ilike(f"%{_query}%")
                            )
                        )
                    ),
                )
            )


class ServiceRevisionSearchFilter(SearchFilter):
    model = ServiceRevision
    _search_criteria: ServiceRevisionQueryCriteria

    queryset = select(ServiceRevision).options(
        joinedload(ServiceRevision.service_revision_tutor)
        .joinedload(Tutor.tutor_ura)
        .joinedload(UserRoleAssociation.ura_user)
    )

    count_queryset = select(func.count(ServiceRevision.id))
    registered_filters = [
        "revision_id",
        "service_id",
        "tutor_id",
        "approval_status",
    ]

    async def revision_id(self):
        self._filters.append(
            getattr(self.model, "id") == self._search_criteria.revision_id
        )

    async def service_id(self):
        self._filters.append(
            getattr(self.model, "service_id") == self._search_criteria.service_id
        )

    async def tutor_id(self):
        self._filters.append(
            getattr(self.model, "tutor_id") == self._search_criteria.tutor_id
        )

    async def approval_status(self):
        approval_status = self._search_criteria.approval_status
        if approval_status and str(approval_status).upper() != "ALL":
            self._filters.append(
                getattr(self.model, "approval_status")
                == str(approval_status).upper()
            )

    def query(self):
        _query = re.sub(
            r"[^a-zA-Z0-9@.\s]+", "", self._search_criteria.query.lower()
        ).strip()
        if _query:
            self._filters.append(
                or_(
                    getattr(self.model, "service_name").ilike(f"%{_query}%"),
                    getattr(self.model, "description").ilike(f"%{_query}%"),
                )
            )

import datetime
import inspect
import re
from functools import reduce

import pytz
from sqlalchemy import BinaryExpression, and_, func, select

from skillbridge.database.models.sqlalchemy.base import BaseModel
from skillbridge.exceptions import InvalidSortError
from skillbridge.utils.common import CommonQueryParams, convert_dict_to_dot_notation


class BaseSearchFilter:
    """
    BaseSearchFilter that include all common functionality.
    """

    model: BaseModel = None
    queryset = None
    count_queryset = None
    _search_criteria = None
    _query: BaseModel = None
    _pagination: dict = {}
    _ignored_filters = [
        "created_at",
        "updated_at",
        "deleted_at",
    ]
    registered_filters: list = []
    default_filters: list = [
        "query",
        "ids",
        "exclude_ids",
        "status",
        "start_date",
        "end_date",
    ]

    async def __new__(cls, *a, **kw):
        instance = super().__new__(cls)
        await instance.__init__(*a, **kw)
        return instance

    async def __init__(self, search_criteria: CommonQueryParams | dict):
        if isinstance(search_criteria, dict):
            search_criteria = convert_dict_to_dot_notation(search_criteria)

        if self.queryset is None:
            # self.queryset = select(self.model).distinct()
            self.queryset = select(self.model)
        if self.count_queryset is None:
            # self.count_queryset = select(func.count(self.model.id)).distinct()
            self.count_queryset = select(func.count(self.model.id))

        self._search_criteria = search_criteria
        self._filters: list = []

        await self.call_registered_filters()

    async def call_registered_filters(self):
        total_registered_filters = self.registered_filters + self.default_filters
        for registered_filter in total_registered_filters:
            if hasattr(self._search_criteria, registered_filter):
                if getattr(self._search_criteria, registered_filter):
                    try:
                        filter_method = getattr(self, registered_filter)
                        if inspect.iscoroutinefunction(filter_method):
                            await filter_method()
                        else:
                            filter_method()
                    except Exception as e:
                        print(f'{str(e)}: "{registered_filter}" not found.')
                        raise e

    def __paginate(self):
        try:
            items_per_page = int(self._search_criteria.items_per_page)
            page_no = int(self._search_criteria.page)
            offset = (page_no - 1) * items_per_page
            if int(self._search_criteria.items_per_page) < 0:
                items_per_page = None
                offset = 0
            self._query = self._query.offset(offset).limit(items_per_page)
        except Exception as e:
            print(e)
        finally:
            return self

    def get_sorting_orders(self):
        """Turn a "field:direction,..." sort string into ORDER BY clauses.

        Anything this cannot honour is the caller's mistake, so it is reported
        as a 400 naming the problem. Previously a sort key that was not a real
        column (``rating:asc``) raised AttributeError, and one with no colon
        (``bogus``) raised ValueError, both of which escaped as an opaque 500.
        """
        orders = []
        if self._search_criteria.sort:
            sort_keys = self._search_criteria.sort.rstrip(",").split(",")
            for s in sort_keys:
                field, _, order = s.partition(":")
                field = field.strip()
                order = (order or "asc").strip().lower()

                if not field or not hasattr(self.model, field):
                    raise InvalidSortError(
                        message=(
                            f"'{s}' is not a supported sort option for this list."
                        ),
                        status_code=400,
                    )
                if order not in ("asc", "desc"):
                    raise InvalidSortError(
                        message=(
                            f"Sort direction '{order}' is not supported; "
                            f"use 'asc' or 'desc'."
                        ),
                        status_code=400,
                    )

                column = getattr(self.model, field)
                if order == "desc":
                    # nulls_last() is specifically for datetime fields
                    # As nulls are returned first when sorted in desc order for datetime fields
                    # It is not the case for other number or string type fields, so those won't be
                    # affected as nulls will be placed last anyway for those.
                    orders.append(column.desc())
                else:
                    # TBD: If nulls_first() is required for asc sorting of datetime fields
                    orders.append(column.asc())

        return orders

    async def get_queryset(self) -> list[BinaryExpression]:
        """Please override this method if you want to add your custom queryset."""

    async def __sort(self):
        if self._search_criteria.sort:
            orders = self.get_sorting_orders()
            self._query = self._query.order_by(*orders)

        return self

    async def get_filters(self):
        if self._filters:
            expr = reduce(and_, self._filters)
            return expr

    async def __filter(self):
        expressions = []
        if hasattr(self, "get_queryset"):
            expr = await self.get_queryset()
            if expr:
                expressions.append(*expr)
        if self._filters:
            expr = await self.get_filters()
            expressions.append(expr)

        # print("--------------------------")
        # print(self.queryset)
        # print("--------------------------")

        self._query = (
            self.queryset.where(*expressions) if expressions else self.queryset
        )

        return self

    async def __count(self):
        expressions = []
        if hasattr(self, "get_queryset"):
            expr = await self.get_queryset()
            if expr:
                expressions.append(*expr)

        if self._filters:
            expr = await self.get_filters()
            expressions.append(expr)

        self._count_query = (
            self.count_queryset.where(*expressions)
            if expressions
            else self.count_queryset
        )

        return self

    async def get_count_query(self):
        count = await self.__count()
        return count._count_query

    async def get_query(self):
        filter = await self.__filter()
        sort = await filter.__sort()
        paginate = sort.__paginate()
        return paginate._query

    def remove_null_value(self, value):
        if isinstance(value, list):
            return [x for x in value if x is not None]
        return []


class SearchFilter(BaseSearchFilter):
    def convert_local_time_to_utc(self, date: str, time_zone: str) -> str:
        # converts local date time to utc time zone
        local = pytz.timezone(time_zone)
        local_dt = local.localize(date, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt

    def format_datetime(self, date, timezone: str = "utc", _type="start") -> str:
        """convert date to utc datetime

        Args:
            date (str): datetime.date
            time_zone (str, optional): timezone. Defaults to "utc".
            date_type (str, optional): start or end. Defaults to "start".

        Returns:
            str: datetime.datetime in utc
        """

        time_format = "00:00:00" if _type == "start" else "23:59:59"
        new_date = datetime.datetime.strptime(
            f"{date} {time_format}", "%Y-%m-%d %H:%M:%S"
        )
        if timezone:
            new_date = self.convert_local_time_to_utc(new_date, timezone)
        return new_date

    def ids(self):
        _ids = self.remove_null_value(self._search_criteria.ids)
        self._filters.append(getattr(self.model, "id").in_(_ids))

    def exclude_ids(self):
        _exclude_ids = self.remove_null_value(self._search_criteria.exclude_ids)
        self._filters.append(getattr(self.model, "id").in_(_exclude_ids))

    def status(self):
        _status = self.remove_null_value(self._search_criteria.status)
        self._filters.append(getattr(self.model, "status").in_(_status))

    def start_date(self):
        _start_date = self.format_datetime(
            self._search_criteria.start_date, _type="start"
        )
        self._filters.append(getattr(self.model, "created_at") >= _start_date)

    def end_date(self):
        _end_date = self.format_datetime(self._search_criteria.end_date, _type="end")
        self._filters.append(getattr(self.model, "created_at") <= _end_date)

    def query(self):
        _query = re.sub('r"[^a-zA-Z0-9^@\.]+', "", self._search_criteria.query.lower())
        self._filters.append(getattr(self.model, "name").icontains(_query))

    def name(self):
        _name = re.sub('r"[^a-zA-Z0-9^@\.]+', "", self._search_criteria.name.lower())
        self._filters.append(getattr(self.model, "name").icontains(_name))

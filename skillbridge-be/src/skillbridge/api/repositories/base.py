import datetime
import math
import os
from typing import List, Tuple
from uuid import UUID

import pytz
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.filters.base import BaseSearchFilter
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.base import BaseModel
from skillbridge.exceptions import NotFoundError
from skillbridge.utils.common import get_valid_data
from skillbridge.utils.renderer import BaseInModel, BaseResponse, BaseSearchCriteria
from skillbridge.utils.utils import with_session

data_limit = int(os.getenv("DATA_LIMIT", 30))


class BaseRepository:
    model: BaseModel = None
    search_filter: BaseSearchFilter = None

    def get_pagination(
        self,
        total_records: int,
        page: int,
        items_per_page: int = data_limit,
    ) -> dict:
        """format pagination detail

        Args:
            total_records (int): total records
            page (int): page no to fetch
            items_per_page (int, optional): no of records to fetch per request. Defaults to data_limit.

        Returns:
            dict: _description_
        """
        current_page = int(page) if page else 1
        total_page = math.ceil(total_records / items_per_page)
        return {
            "current_page": current_page,
            "total_page": total_page,
            "total_records": total_records,
            "items_per_page": items_per_page,
        }

    async def get_paginated_results(
        self,
        query: BaseSearchCriteria,
    ) -> BaseResponse:
        if self.search_filter:
            results = await self.filter(query)
            total_records = await self.count(query)
            metadata = self.get_pagination(
                total_records, page=query.page, items_per_page=query.items_per_page
            )
            response: dict = {
                "success": True,
                "message": f"{self.model.__name__}s have been fetched.",
                "metadata": metadata,
                "data": results,
            }
            return response
        else:
            limit, offset = self.get_limit_offset(
                page=query.page, items_per_page=query.items_per_page
            )
            response = await self.get_all(query, offset=offset, limit=limit)
            return response

    def format_start_date_end_date(self, payload: dict, time_zone: str) -> str:
        # formats date time to utc time
        start_date = None
        end_date = None
        date_time_format = "%Y-%m-%d %H:%M:%S"
        if "start_date" in payload and payload["start_date"]:
            start_date = datetime.datetime.strptime(
                "{} {}".format(payload["start_date"], "00:00:00"), date_time_format
            )
            if time_zone:
                start_date = self.convert_local_time_to_utc(start_date, time_zone)

        if "end_date" in payload and payload["end_date"]:
            end_date = datetime.datetime.strptime(
                "{} {}".format(payload["end_date"], "23:59:59"), date_time_format
            )
            if time_zone:
                end_date = self.convert_local_time_to_utc(end_date, time_zone)

        if (
            "start_date" in payload
            and payload["start_date"]
            and ("end_date" not in payload or not payload["end_date"])
        ):
            end_date = datetime.datetime.utcnow()

        return start_date, end_date

    def convert_local_time_to_utc(self, date: str, time_zone: str) -> str:
        """converts local date time to utc time zone ::time_zone example: Asia/Kathmandu

        Args:
            date (str): datetime in str
            time_zone (str): timezone to convert

        Returns:
            str: converted utc datetime
        """
        local = pytz.timezone(time_zone)
        local_dt = local.localize(date, is_dst=None)
        utc_dt = local_dt.astimezone(pytz.utc)
        return utc_dt

    def current_date_time(self) -> str:
        """current datetime in utc

        Returns:
            str: utc time
        """
        return datetime.datetime.now(datetime.timezone.utc)

    def get_limit_offset(self, page: int, items_per_page: int = data_limit) -> tuple:
        """get limit and offset for query

        Args:
            page (int): page number
            limit (int, optional): how many records to fetch per page. Defaults to data_limit.

        Returns:
            tuple: limit, offset
        """
        page = int(page) if page else 1
        offset = 0
        if page > 1:
            offset = items_per_page * (page - 1)
        return items_per_page, offset

    # async def count(self, offset: int, limit: int) -> List[BaseModel]:
    #     async with get_session() as session:
    #         query = await session.execute(
    #             select(func.count(self.model.id)).offset(offset).limit(limit)
    #         )
    #         return query.scalar()

    # TODO: refactor and support ordering
    async def get_all(self, query, offset: int, limit: int) -> List[BaseModel]:
        async with get_session() as session:
            records_query = await session.execute(
                select(self.model).offset(offset).limit(limit)
            )
            scans = records_query.scalars().all()
            count_query = await session.execute(select(func.count(self.model.id)))
            total_records = count_query.scalar()

            metadata = self.get_pagination(
                total_records, page=query.page, items_per_page=query.items_per_page
            )
            response: dict = {
                "success": True,
                "message": f"{self.model.__name__}s have been fetched.",
                "metadata": metadata,
                "data": scans,
            }
            return response

    @with_session
    async def get_all_raw_data(
        self,
        model: BaseModel = None,
        session: AsyncSession = None,
    ):
        model = model if model else self.model
        records = (await session.execute(select(model))).scalars().unique().all()
        return records

    async def count(self, query: BaseSearchCriteria) -> List[BaseModel]:
        async with get_session() as session:
            count_filter: BaseSearchFilter = await self.search_filter(query)
            count_query = await count_filter.get_count_query()
            query = await session.execute(count_query)
            return query.scalar()

    async def filter(self, query: BaseSearchCriteria) -> List[BaseModel]:
        async with get_session() as session:
            search_filter: BaseSearchFilter = await self.search_filter(query)
            search_query = await search_filter.get_query()
            search_query = await session.execute(search_query)
            results = search_query.scalars().unique().all()
            # if hasattr(query, "info"):
            #     selected_fields = set(get_only_selected_fields(self.model, query.info))
            #     db_relations_fields = set(get_db_relations(self.model))
            #     relations_selected = selected_fields & db_relations_fields
            #     for result in results:
            #         for relation_selected in relations_selected:
            #             if hasattr(result, relation_selected):
            #                 data = getattr(result, relation_selected)
            #                 setattr(result, relation_selected, data)

            return results

    @with_session
    async def get(
        self,
        _id: UUID,
        model: BaseModel = None,
        session: AsyncSession = None,
    ):
        model = model if model else self.model
        db_object = await session.get(model, _id)
        if not db_object:
            raise NotFoundError(f"{model.__name__} not found.")

        response: dict = {
            "success": True,
            "message": f"{model.__name__} has been fetched.",
            "metadata": {},
            "data": db_object,
        }

        return response

    async def create(
        self,
        data: BaseModel,
        model: BaseModel = None,
        session: AsyncSession = None,
        message=None,
    ):
        model = model if model else self.model
        valid_data = get_valid_data(data, model)
        model = model if model else model
        db_object = model(**valid_data)

        session.add(db_object)
        await session.flush()
        await session.refresh(db_object)
        response: dict = {
            "success": True,
            "message": message if message else f"{model.__name__} has been created.",
            "metadata": {},
            "data": db_object,
        }
        return response

    @with_session
    async def update(
        self,
        _id: int,
        data: BaseModel,
        model: BaseModel = None,
        session: AsyncSession = None,
    ):
        model = model if model else self.model
        db_object = await session.get(model, _id)
        if not db_object:
            raise NotFoundError(f"{model.__name__} not found.")

        valid_data = get_valid_data(data, model)

        for key, value in valid_data.items():
            if value is not None:
                setattr(db_object, key, value)

        session.add(db_object)
        await session.flush()
        await session.refresh(db_object)
        response: dict = {
            "success": True,
            "message": f"{model.__name__} has been updated.",
            "metadata": {},
            "data": db_object,
        }

        return response

    @with_session
    async def delete(
        self,
        _id: int,
        data: BaseInModel = None,
        model: BaseModel = None,
        session: AsyncSession = None,
    ):
        model = model if model else self.model
        db_object = await session.get(model, _id)
        if not db_object:
            raise NotFoundError(f"{model.__name__} not found.")
        obj_to_delete = db_object
        await session.delete(db_object)
        response: dict = {
            "success": True,
            "message": f"{model.__name__} has been deleted.",
            "metadata": {},
            "data": obj_to_delete,
        }
        return response

    async def upsert(
        self,
        data,
        constraint_name=None,
        returning_cols: Tuple[str] = None,
        session: AsyncSession = None,
    ):
        """
        Inserts/Updates a single row in a table based on the specified constraint
        """

        valid_data = get_valid_data(data, self.model)

        if not constraint_name:
            constraint_name = f"{self.model.__tablename__}_upsert"  # TODO: Check this

        insert_stmt = insert(self.model).values(**data.model_dump())

        # TODO: Add option for specified list of index_elements as an alternative to constraint
        upsert_stmt = insert_stmt.on_conflict_do_update(
            constraint=constraint_name,
            set_={
                x.name: x for x in insert_stmt.excluded if x.name in valid_data.keys()
            },
        ).returning(self.model)
        result_db_obj = (await session.execute(upsert_stmt)).scalars().first()
        # returning_result = (
        #     await session.execute(
        #         upsert_stmt.returning(
        #             *[Column(x) for x in returning_cols] if returning_cols else "*"
        #         )
        #     )
        # ).fetchone()

        return {
            "success": True,
            "message": f"{self.model.__name__} has been upserted.",
            "metadata": {},
            "data": result_db_obj,
        }

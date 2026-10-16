from functools import wraps
from typing import Iterable

from sqlalchemy import ColumnExpressionArgument, select

from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.base import BaseModel


def convert_to_field_and_order(input_string):
    mapping = {"asc": 1, "desc": -1}
    parts = input_string.split(":")

    if len(parts) == 2:
        field_name, order_string = parts
        order = mapping.get(order_string.lower(), None)
        if order is not None:
            return field_name, order

    raise ValueError("Invalid sort input format")


async def update_or_create(
    session, model: BaseModel, filters: Iterable[ColumnExpressionArgument], data: dict
):
    query = select(model).where(*filters)
    search_query = await session.execute(query)
    instance = search_query.scalar()

    if not instance:
        instance = model(**data)
        session.add(instance)

    else:
        for k, v in data.items():
            setattr(instance, k, v)

    return instance


def with_session(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        if not kwargs.get("session"):
            async with get_session() as session:
                kwargs["session"] = session
                result = await func(*args, **kwargs)
                await session.commit()
                return result
        else:
            result = await func(*args, **kwargs)
            return result

    return wrapper

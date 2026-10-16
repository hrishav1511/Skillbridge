test_emails = [
    "justnotest3@gmail.com",
    "anu@kodiary.com",
    "anish.tekvortex@gmail.com",
]

import asyncio
import base64
import re
import uuid
from collections import namedtuple
from typing import Any, Awaitable

from pydantic import BaseModel as BasePydanticModel
from pydantic import field_validator, model_validator
from sqlalchemy.inspection import inspect

from skillbridge.database.models.sqlalchemy.base import BaseModel
from skillbridge.utils.renderer import PaginationType, Status


def generate_slug(input_string):
    # Convert to lowercase and replace spaces with hyphens
    slug = input_string.lower().replace(" ", "-")

    # Remove special characters using regex
    slug = re.sub(r"[^\w\-]", "", slug)

    return slug


def convert_camel_case(name: str):
    pattern = re.compile(r"(?<!^)(?=[A-Z])")
    name = pattern.sub("_", name).lower()
    return name


def get_db_relations(db_baseclass_name: BaseModel):
    db_relations_fields = inspect(db_baseclass_name).relationships.keys()
    return db_relations_fields


def get_only_selected_fields(
    db_baseclass_name: BaseModel,
):
    from sqlalchemy import inspect

    inst = inspect(db_baseclass_name)
    attr_names = [c_attr.key for c_attr in inst.mapper.column_attrs]

    db_relations_fields = get_db_relations(db_baseclass_name)
    all_db_fields = attr_names + db_relations_fields

    selected_fields = []

    # if not info:
    #     return selected_fields

    # for first_field in info.selected_fields[0].selections:
    #     if isinstance(first_field, InlineFragment):
    #         for field in first_field.selections:
    #             field_name = convert_camel_case(field.name)
    #             if field_name in all_db_fields:
    #                 selected_fields.append(field_name)
    #     else:
    #         field_name = convert_camel_case(first_field.name)
    #         if field_name == "data":
    #             for field in first_field.selections:
    #                 field_name = convert_camel_case(field.name)
    #                 if field_name in all_db_fields:
    #                     selected_fields.append(field_name)

    # for second_field in info.selected_fields[0].selections[0].selections:
    #     field_name = convert_camel_case(second_field.name)
    #     if field_name in all_db_fields:
    #         selected_fields.append(field_name)

    #     if field_name == "data":
    #         for field in second_field.selections:
    #             field_name = convert_camel_case(field.name)
    #             if field_name in all_db_fields:
    #                 selected_fields.append(field_name)

    return selected_fields


def get_valid_data(model_data_object: BasePydanticModel, model_class: BaseModel):
    data_dict = {}
    for column in model_class.__table__.columns:
        try:
            data_dict[column.name] = getattr(model_data_object, column.name)
        except:
            pass
    return data_dict


def convert_dict_to_dot_notation(data: dict):
    if isinstance(data, dict):
        data = namedtuple("JustnotarizedConversionClass", data.keys())(*data.values())
    return data


def convert_dict_to_dot_notation(data: dict):
    if isinstance(data, dict):
        data = namedtuple("JustnotarizedConversionClass", data.keys())(*data.values())
    return data


def convert_dict_to_dot_notation(data: dict):
    if isinstance(data, dict):
        data = namedtuple("JustnotarizedConversionClass", data.keys())(*data.values())
    return data


async def common_parameters(
    query: str | None = None,
    status: list[Status] | None = None,
    ids: list[str] | None = None,
    exclude_ids: list[str] | None = None,
    user_ids: list[str] | None = None,
    excluded_user_ids: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sort: str = "created_at:desc",
    items_per_page: int = 10,
    page: int = 1,
):
    query = {
        "ids": ids,
        "query": query,
        "page": page,
        "items_per_page": items_per_page,
        "sort": sort,
        "status": status,
        "exclude_ids": exclude_ids,
        "excluded_user_ids": excluded_user_ids,
        "user_ids": user_ids,
        "start_date": start_date,
        "end_date": end_date,
    }
    return query


class CommonQueryParams:
    def __init__(
        self,
        query: str | None = None,
        status: list[Status] | None = None,
        ids: list[str] | None = None,
        exclude_ids: list[str] | None = None,
        user_ids: list[str] | None = None,
        excluded_user_ids: list[str] | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        sort: str = "created_at:desc",
        items_per_page: int = 10,
        page: int = 1,
    ):
        self.query = query
        self.status = status
        self.ids = ids
        self.exclude_ids = exclude_ids
        self.user_ids = user_ids
        self.excluded_user_ids = excluded_user_ids
        self.start_date = start_date
        self.end_date = end_date
        self.sort = sort
        self.items_per_page = items_per_page
        self.page = page


def format_response(response: dict, format_type=None, message=None):
    formatted_response: dict = {}
    for k, v in response.items():
        if k == "message" and message:
            formatted_response.update({k: message})

        elif k == "metadata":
            if v:
                formatted_response.update({k: PaginationType(**v)})
        else:
            formatted_response.update({k: v})

    if format_type == "delete":
        formatted_response.pop("data")

    return formatted_response


def sqlalchemy_row_to_dict(row):
    return {column: getattr(row, column) for column in row.__table__.columns.keys()}


class PasswordValidator(BasePydanticModel):
    password: str
    confirm_password: str

    @field_validator("password")
    def validate_password(cls, value):
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return value

    @field_validator("password")
    def validate_password_complexity(cls, value):
        if not any(c.isupper() for c in value):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in value):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in value):
            raise ValueError("Password must contain at least one digit")
        if not any(c in '!@#$%^&*(),.?":{}|<>' for c in value):
            raise ValueError("Password must contain at least one special character")
        return value

    @model_validator(mode="after")
    def passwords_match(self):
        if self.confirm_password != self.password:
            raise ValueError("Passwords do not match")
        return self


def uuid_to_base64(input_uuid):
    # Convert the input UUID to bytes
    uuid_bytes = input_uuid.bytes

    # Encode the bytes in base64
    base64_uuid = base64.urlsafe_b64encode(uuid_bytes).decode("utf-8")

    return base64_uuid


def base64_to_uuid(base64_str):
    # Decode the base64 string to bytes
    uuid_bytes = base64.urlsafe_b64decode(base64_str.encode("utf-8"))

    # Convert the bytes to a UUID
    decoded_uuid = uuid.UUID(bytes=uuid_bytes)

    return decoded_uuid


async def run_coroutine_in_sequence(*functions: Awaitable[Any]) -> None:
    for function in functions:
        await function


async def run_coroutine_in_parallel(*functions: Awaitable[Any]) -> None:
    await asyncio.gather(*functions)


def snake_to_camel(input_string):
    if input_string:
        parts = input_string.split("_")
        return parts[0] + "".join(word.capitalize() for word in parts[1:])

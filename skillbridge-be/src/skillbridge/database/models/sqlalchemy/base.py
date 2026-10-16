import uuid
from datetime import datetime, timezone

from sqlalchemy import CHAR, Column, DateTime, ForeignKey, String, func
from sqlalchemy.orm import declared_attr, relationship
from sqlalchemy.types import TypeDecorator

from skillbridge.utils.renderer import Status
from . import Base


class UUIDType(TypeDecorator):
    """Platform-independent UUID type. Uses CHAR(36) for MySQL."""

    impl = CHAR(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return uuid.UUID(value)


class BaseModelMixin:
    @declared_attr
    def created_by_id(cls):
        return Column(
            UUIDType,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def updated_by_id(cls):
        return Column(
            UUIDType,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr
    def created_by(cls):
        return relationship(
            "User",
            foreign_keys=[cls.created_by_id],
            backref=f"{cls.__tablename__}_created_by",
            lazy="immediate",
        )

    @declared_attr
    def updated_by(cls):
        return relationship(
            "User",
            foreign_keys=[cls.updated_by_id],
            backref=f"{cls.__tablename__}_updated_by",
            lazy="immediate",
        )


class BaseModel(Base):
    __abstract__ = True

    id = Column(UUIDType, primary_key=True, default=uuid.uuid4)
    status = Column(String(50), default=Status.ACTIVE)
    # MySQL's DATETIME carries no offset, so `timezone=True` is a no-op there and
    # `func.now()` records the database server's local clock. Defaulting in
    # Python keeps every row written through the ORM in explicit UTC; the server
    # default stays as a fallback for rows inserted outside the ORM.
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=True,
    )
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def to_dict(self):
        dict_obj = {
            column.name: getattr(self, column.name) for column in self.__table__.columns
        }
        return dict_obj

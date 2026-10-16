import enum

from sqlalchemy import Column, String, Text
from sqlalchemy.orm import relationship

from skillbridge.database.models.sqlalchemy.base import BaseModel, BaseModelMixin


class ROLE_ENUM(str, enum.Enum):
    TUTOR = "TUTOR"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"
    STUDENT = "STUDENT"

    def __str__(self):
        return self.value


class Role(BaseModel, BaseModelMixin):
    __tablename__ = "roles"
    # __table_args__ = {'extend_existing': True}

    title = Column(String(255), default=ROLE_ENUM.STUDENT, unique=True)
    slug = Column(String(255), nullable=False)
    description = Column(Text)
    role_ura = relationship(
        "UserRoleAssociation",
        back_populates="ura_role",
        cascade="delete, merge, save-update",
        lazy="noload",
    )

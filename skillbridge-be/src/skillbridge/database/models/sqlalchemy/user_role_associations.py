from sqlalchemy import UUID, Column, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from skillbridge.database.models.sqlalchemy.base import (
    BaseModel,
    BaseModelMixin,
    UUIDType,
)


class UserRoleAssociation(BaseModel, BaseModelMixin):
    __tablename__ = "user_role_associations"
    __table_args__ = (
        UniqueConstraint("user_id", "role_id", name="uq_user_role_association"),
    )

    user_id = Column(
        UUIDType,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    role_id = Column(
        UUIDType, ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )

    student_id = Column(
        UUIDType,
        ForeignKey("students.id", ondelete="CASCADE"),
        nullable=True,
    )
    tutor_id = Column(
        UUIDType,
        ForeignKey("tutors.id", ondelete="CASCADE"),
        nullable=True,
    )

    ura_user = relationship(
        "User",
        foreign_keys=[user_id],
        back_populates="user_ura",
        lazy="noload",
    )

    ura_role = relationship(
        "Role",
        foreign_keys=[role_id],
        back_populates="role_ura",
        lazy="noload",
    )
    ura_student = relationship(
        "Student",
        foreign_keys=[student_id],
        back_populates="student_ura",
        lazy="noload",
    )

    ura_tutor = relationship(
        "Tutor",
        foreign_keys=[tutor_id],
        back_populates="tutor_ura",
        lazy="noload",
    )

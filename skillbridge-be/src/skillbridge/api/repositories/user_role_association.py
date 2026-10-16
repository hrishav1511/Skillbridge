import json
from uuid import UUID

from fastapi import status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.user import UserSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.schemas.user import (
    GETPendingSocketRequestOutput,
    UpdateUserModel,
    UpdateUserProfileModel,
)
from skillbridge.api.validators.user import UpdateUserInputValidator
from skillbridge.config import settings
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.roles import Role
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import DuplicateUserError, NotFoundError, NotRegisteredError
from skillbridge.utils.utils import with_session


class UserRoleAssociationRepository(BaseRepository):
    model = UserRoleAssociation
    search_filter = UserSearchFilter

    async def check_duplicate_user_role(
        self,
        user_id: UUID,
        role_id: UUID,
        session: AsyncSession = None,
    ):
        user_role = (
            (
                await session.execute(
                    select(UserRoleAssociation).where(
                        UserRoleAssociation.user_id == user_id,
                        UserRoleAssociation.role_id == role_id,
                    )
                )
            )
            .scalars()
            .first()
        )

        if user_role:
            raise DuplicateUserError(
                message="User with this role already exists.",
                status_code=status.HTTP_406_NOT_ACCEPTABLE,
            )
        return True

    async def check_duplicate_user(
        self,
        email: str,
        role_id: UUID | None = None,
        session: AsyncSession = None,
    ):
        user = (
            (
                await session.execute(
                    select(self.model).where(
                        or_(
                            self.model.email == email,
                        )
                    )
                )
            )
            .scalars()
            .first()
        )

        if user:
            user_role_check = await self.check_duplicate_user_role(
                user_id=user.id,
                role_id=role_id,
                session=session,
            )

        return user

    async def get_all_users(self):
        async with get_session() as session:
            users = (await session.execute(select(self.model))).scalars().all()
            return users

    @with_session
    async def get(
        self,
        _id: UUID,
        model: BaseModel = None,
        session: AsyncSession = None,
    ):
        model = model if model else self.model
        db_object = (
            (await session.execute(select(self.model).where(self.model.id == _id)))
            .scalars()
            .first()
        )
        if not db_object:
            raise NotFoundError(f"{model.__name__} not found.")

        response: dict = {
            "success": True,
            "message": f"{model.__name__} has been fetched.",
            "metadata": {},
            "data": db_object,
        }

        return response

    async def update_user(
        self,
        user_input: UpdateUserInputValidator,
    ):
        async with get_session() as session:
            if user_input.name:
                user_data = UpdateUserModel(name=user_input.name)
                user = await self.update(
                    _id=user_input.user_id,
                    data=user_data,
                    session=session,
                )

            else:
                user = await self.get(
                    _id=user_input.user_id,
                    session=session,
                )

            await session.commit()
            return user

    @with_session
    async def check_registered_user(
        self,
        email: str,
        session: AsyncSession = None,
    ):
        registered_user = (
            (
                await session.execute(
                    select(self.model).where(
                        self.model.email == email,
                        self.model.has_registered == True,
                    )
                )
            )
            .scalars()
            .first()
        )

        if not registered_user:
            raise NotRegisteredError(
                status_code=status.HTTP_401_UNAUTHORIZED,
                message="You are not yet registered.",
            )

    async def is_user_admin(
        self,
        user_id: UUID,
        session: AsyncSession = None,
    ) -> bool:
        """Return True for administrator and super-administrator accounts."""
        query = (
            select(UserRoleAssociation)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                func.lower(Role.slug).in_(("admin", "super_admin")),
            )
        )

        if session is None:
            async with get_session() as session:
                result = await session.execute(query)
                return result.scalars().first() is not None

        result = await session.execute(query)
        return result.scalars().first() is not None

    async def get_user_id_by_tutor_id(
        self,
        tutor_id: UUID,
        session: AsyncSession = None,
    ) -> UUID | None:
        """Get the user_id associated with a tutor_id from UserRoleAssociation table"""
        query = select(UserRoleAssociation.user_id).where(
            UserRoleAssociation.tutor_id == tutor_id
        )

        if session is None:
            async with get_session() as session:
                return (await session.execute(query)).scalar_one_or_none()

        return (await session.execute(query)).scalar_one_or_none()

    async def get_tutor_account_status(
        self,
        tutor_id: UUID,
        session: AsyncSession = None,
    ) -> str | None:
        query = (
            select(User.status)
            .join(UserRoleAssociation, UserRoleAssociation.user_id == User.id)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.tutor_id == tutor_id,
                func.lower(Role.slug) == "tutor",
            )
        )
        if session is None:
            async with get_session() as session:
                return (await session.execute(query)).scalar_one_or_none()
        return (await session.execute(query)).scalar_one_or_none()

    @with_session
    async def get_tutor_id_by_user_id(
        self,
        user_id: UUID,
        session: AsyncSession = None,
    ) -> UUID | None:
        """Get the tutor_id associated with a user_id when that user is a tutor."""
        query = (
            select(UserRoleAssociation.tutor_id)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.tutor_id.is_not(None),
                func.lower(Role.slug) == "tutor",
            )
        )


        return (await session.execute(query)).scalar_one_or_none()

    @with_session
    async def get_student_id_by_user_id(
        self,
        user_id: UUID,
        session: AsyncSession = None,
    ) -> UUID | None:
        """Get the student profile associated with a user account."""
        query = (
            select(UserRoleAssociation.student_id)
            .join(Role, UserRoleAssociation.role_id == Role.id)
            .where(
                UserRoleAssociation.user_id == user_id,
                UserRoleAssociation.student_id.is_not(None),
                func.lower(Role.slug) == "student",
            )
        )
        return (await session.execute(query)).scalar_one_or_none()

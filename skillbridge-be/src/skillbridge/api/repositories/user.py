import json
from uuid import UUID

from fastapi import status
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from skillbridge.api.filters.user import UserSearchFilter
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.user_role_association import (
    UserRoleAssociationRepository,
)
from skillbridge.api.schemas.user import (
    GETPendingSocketRequestOutput,
    UpdateUserModel,
    UpdateUserProfileModel,
)
from skillbridge.api.validators.user import UpdateUserInputValidator
from skillbridge.config import settings
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import DuplicateUserError, NotFoundError, NotRegisteredError
from skillbridge.utils.utils import with_session


class UserRepository(BaseRepository):
    model = User
    search_filter = UserSearchFilter

    @with_session
    async def get_user_from_email(
        self,
        email: str,
        session: AsyncSession = None,
    ):
        user = (
            (
                await session.execute(
                    select(self.model).where(
                        self.model.email == email,
                    )
                )
            )
            .scalars()
            .first()
        )

        return user

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
            user_role_check = (
                await UserRoleAssociationRepository().check_duplicate_user_role(
                    user_id=user.id,
                    role_id=role_id,
                    session=session,
                )
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

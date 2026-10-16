from uuid import UUID

from fastapi import status
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from skillbridge.api.repositories.auth.base import AuthService
from skillbridge.api.repositories.auth.token import TokenRepository
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.schemas.token import RefreshTokenModel
from skillbridge.api.validators.login import LoginInputValidator
from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.refresh_tokens import RefreshToken
from skillbridge.database.models.sqlalchemy.user_role_associations import (
    UserRoleAssociation,
)
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import InvalidCredentialsError, NotRegisteredError
from skillbridge.utils.utils import with_session


class LoginRepository(BaseRepository):

    @with_session
    async def check_user_register_status(
        self,
        email: str,
        role_id: UUID | None,
        login_data: LoginInputValidator,
        session: AsyncSession = None,
    ):
        user = (
            (
                await session.execute(
                    select(User).where(
                        User.email == email,
                        User.has_registered == True,
                    )
                )
            )
            .scalars()
            .first()
        )
        if not user:
            raise NotRegisteredError(
                message="The User has not been registered yet.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        if str(user.status).upper() == "INACTIVE":
            raise NotRegisteredError(
                message="This tutor account is temporarily disabled. Please contact an administrator.",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        if not AuthService().verify_password(login_data.password, user.password):
            raise InvalidCredentialsError(
                message="Invalid email or password.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )
        association_query = (
            select(UserRoleAssociation)
            .options(
                joinedload(UserRoleAssociation.ura_user),
                joinedload(UserRoleAssociation.ura_role),
                # The avatar lives on the tutor/student row, so load it here
                # rather than making the client fetch a profile just to render
                # the navbar icon.
                joinedload(UserRoleAssociation.ura_tutor),
                joinedload(UserRoleAssociation.ura_student),
            )
            .where(UserRoleAssociation.user_id == user.id)
        )
        if role_id is not None:
            association_query = association_query.where(
                UserRoleAssociation.role_id == role_id
            )
        user_role_association = (
            (
                await session.execute(association_query)
            )
            .scalars()
            .first()
        )
        if not user_role_association:
            raise NotRegisteredError(
                message="The User has not been registered for this role yet.",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return user_role_association

    async def login(
        self,
        login_data: LoginInputValidator,
    ):
        async with get_session() as session:
            user_role_association = await self.check_user_register_status(
                email=login_data.email,
                role_id=login_data.role_id,
                login_data=login_data,
                session=session,
            )

            # Create tokens
            tokens = TokenRepository().create_tokens(str(user_role_association.user_id),)

            refresh_token = RefreshTokenModel(
                token=tokens["refresh_token"],
                user_id=user_role_association.user_id,
                expires_at=tokens["refresh_token_expires"],
            )
            await self.create(model=RefreshToken, data=refresh_token, session=session)
            await session.flush()  # Ensure the refresh token is saved before committing
            await session.commit()

            return user_role_association, tokens
          

import json

from fastapi import status
from sqlalchemy import or_, select

from safar.api.repositories.auth.auth0 import Auth0Manager, HttpWrapper
from safar.api.repositories.base import BaseRepository
from safar.api.validators.password_forget import PasswordForgetResetInputValidator
from safar.api.validators.password_reset import PasswordResetInputValidator
from safar.config import settings
from safar.database.db.database import get_session
from safar.database.models.sqlalchemy.users import User
from safar.exceptions import InvalidCredentialsError, NotFoundError


class PasswordResetRepository(BaseRepository):
    async def verify_password(
        self,
        email: str,
        password: str,
    ):
        url = f"https://{settings.AUTH0_DOMAIN}/oauth/token"
        payload = {
            "grant_type": "password",
            "client_id": settings.AUTH0_MGMT_API_CLIENT_ID,
            "client_secret": settings.AUTH0_MGMT_API_CLIENT_SECRET,
            "audience": settings.AUTH0_API_AUDIENCE,
            "username": email,
            "password": password,
            "scope": "openid offline_access",
        }
        headers = {"content-type": "application/x-www-form-urlencoded"}

        async with HttpWrapper() as http_wrapper:
            response = await http_wrapper.parse_response(
                http_wrapper.post,
                url=url,
                headers=headers,
                json=payload,
            )

            if response["success"] == False:
                # raise ValueError((response["data"]).get("error", {}))
                raise InvalidCredentialsError(
                    message=response["data"]["error_description"],
                    status_code=response["status_code"],
                )
        return True

    async def reset_password(
        self,
        password_reset_input: PasswordResetInputValidator,
    ):
        user: User = (
            await self.get(
                _id=password_reset_input.user_id,
                model=User,
            )
        )["data"]
        await self.verify_password(
            email=user.email,
            password=password_reset_input.current_password,
        )
        auth0_client = Auth0Manager(
            domain=settings.AUTH0_DOMAIN,
            client_id=settings.AUTH0_MGMT_API_CLIENT_ID,
            client_secret=settings.AUTH0_MGMT_API_CLIENT_SECRET,
            audience=settings.AUTH0_API_AUDIENCE,
        )
        token = await auth0_client.get_mgmt_access_token()

        # Send password reset email to the user via Auth0 Management API
        url = f"{settings.AUTH0_API_AUDIENCE}users/{user.auth_id}"
        token = token["access_token"]
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        payload = {
            "password": password_reset_input.confirm_new_password,
        }

        async with HttpWrapper() as http_wrapper:
            response = await http_wrapper.parse_response(
                http_wrapper.patch,
                url=url,
                headers=headers,
                json=json.dumps(payload),
            )
        return True

    async def reset_forget_password(
        self,
        password_forget_reset_input: PasswordForgetResetInputValidator,
    ):
        async with get_session() as session:
            user: User = (
                (
                    await session.execute(
                        select(User).where(
                            or_(
                                User.email == password_forget_reset_input.email,
                                # User.phone == password_forget_reset_input.phone,
                            )
                        )
                    )
                )
                .scalars()
                .first()
            )
            if not user:
                raise NotFoundError(
                    message="User not found for the provided email/phone",
                    status_code=status.HTTP_404_NOT_FOUND,
                )

            auth0_client = Auth0Manager(
                domain=settings.AUTH0_DOMAIN,
                client_id=settings.AUTH0_MGMT_API_CLIENT_ID,
                client_secret=settings.AUTH0_MGMT_API_CLIENT_SECRET,
                audience=settings.AUTH0_API_AUDIENCE,
            )
            token = await auth0_client.get_mgmt_access_token()

            # Send password reset email to the user via Auth0 Management API
            url = f"{settings.AUTH0_API_AUDIENCE}users/{user.auth_id}"
            token = token["access_token"]
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            payload = {
                "password": password_forget_reset_input.confirm_new_password,
            }

            async with HttpWrapper() as http_wrapper:
                response = await http_wrapper.parse_response(
                    http_wrapper.patch,
                    url=url,
                    headers=headers,
                    json=json.dumps(payload),
                )
            return True

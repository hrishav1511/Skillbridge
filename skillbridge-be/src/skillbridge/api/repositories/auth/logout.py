from jose import jwt

from safar.api.schemas.user import UserLogoutInput, UserLogoutResponse
from safar.database.db.database import get_session


class LogoutRepository:
    async def logout_user(
        self,
        logout_input: UserLogoutInput,
    ):
        from safar.api.repositories.auth.token import (
            ALGORITHM,
            SECRET_KEY,
            TokenRepository,
        )

        async with get_session() as session:
            access_token_payload = jwt.decode(
                logout_input.access_token, SECRET_KEY, algorithms=[ALGORITHM]
            )
            jti = access_token_payload.get("jti")
            if jti:
                await TokenRepository().revoke_token(jti, session=session)

            refresh_token_payload = jwt.decode(
                logout_input.refresh_token, SECRET_KEY, algorithms=[ALGORITHM]
            )
            jti = refresh_token_payload.get("jti")
            if jti:
                await TokenRepository().revoke_token(jti, session=session)

            await session.commit()

        response = UserLogoutResponse(
            success=True,
            message="User succesfully logged out.",
        )
        return response

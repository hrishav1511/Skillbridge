from tokenize import TokenInfo
from typing import Dict, Optional, Any
import uuid
from uuid import UUID
from datetime import datetime, timedelta, timezone
from functools import wraps

# from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import bcrypt
from fastapi import HTTPException, Request, WebSocket, WebSocketException, status, Depends
from fastapi.openapi.models import HTTPBearer
from fastapi.security.utils import get_authorization_scheme_param
from jose import JWTError, jwt
from pydantic import BaseModel, ConfigDict, ValidationError
from sqlalchemy import and_, select

from skillbridge.api.repositories.auth.token_verifier import TokenVerifier
from skillbridge.api.repositories.base import BaseRepository
from skillbridge.api.repositories.user import UserRepository
from skillbridge.api.schemas.login import CodeInput
from skillbridge.api.schemas.token import  TokenPayload
from skillbridge.api.schemas.user import NewTokenResponse, NewTokensInput, NewTokensOutput
from skillbridge.api.repositories.auth.config import auth_config
from skillbridge.database.db.database import get_session

# from safar.database.models.sqlalchemy.token_blacklist import TokenBlacklist
from skillbridge.database.models.sqlalchemy.refresh_tokens import RefreshToken
from skillbridge.database.models.sqlalchemy.users import User
from skillbridge.exceptions import (
    AuthenticationError,
    InvalidCredentialsError,
    InvalidTokenException,
    TokenExpiredException,
    UnAuthorizedError,
)

bearer_scheme = HTTPBearer()
# SECRET_KEY = secrets.token_hex(32)
SECRET_KEY = auth_config.SECRET_KEY




class Header(BaseModel):
    token: HTTPBearer

    model_config = ConfigDict(arbitrary_types_allowed=True)


class TokenRepository(BaseRepository):
    def __init__(self):
        self.token_verifier = TokenVerifier()
        self.secret_key = auth_config.JWT_SECRET_KEY
    
    @staticmethod
    def hash_password(password: str) -> str:
        salt = bcrypt.gensalt(rounds=auth_config.BCRYPT_ROUNDS)
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            password.encode('utf-8'),
            hashed_password.encode('utf-8')
        )
    
    @staticmethod
    def create_tokens(user_id: str) -> Dict[str, str]:
        # Generate JWT ID
        jti = str(uuid.uuid4())
        
        issued_at = datetime.now(timezone.utc)

        # Access token
        access_token_exp = issued_at + timedelta(
            minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        access_token_payload = TokenPayload(
            sub=str(user_id),
            exp=access_token_exp,
            iat=issued_at,
            type="access",
            jti=str(uuid.uuid4())
        )
        access_token = jwt.encode(
            access_token_payload.model_dump(),
            auth_config.JWT_SECRET_KEY,
            algorithm=auth_config.JWT_ALGORITHM
        )
        
        # Refresh token
        refresh_token_exp = issued_at + timedelta(
            days=auth_config.REFRESH_TOKEN_EXPIRE_DAYS
        )
        refresh_token_payload = TokenPayload(
            sub=str(user_id),
            exp=refresh_token_exp,
            iat=issued_at,
            type="refresh",
            jti=str(uuid.uuid4())
        )
        refresh_token = jwt.encode(
            refresh_token_payload.model_dump(),
            auth_config.JWT_SECRET_KEY,
            algorithm=auth_config.JWT_ALGORITHM
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "access_token_expires": access_token_exp,
            "refresh_token_expires": refresh_token_exp
        }
    
    
    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> Dict[str, str]:
        try:
            async with get_session() as session:

                # Decode refresh token
                payload = jwt.decode(
                    refresh_token,
                    auth_config.JWT_SECRET_KEY,
                    algorithms=[auth_config.JWT_ALGORITHM]
                )
                token_data = TokenPayload(**payload)
                if token_data.type != "refresh":
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid token type"
                    )
                
                # Check if token exists and not revoked
                stmt = select(RefreshToken).where(
                    and_(
                        RefreshToken.token == refresh_token,
                        RefreshToken.revoked == False
                    )
                )
                
                result = await session.execute(stmt)
                stored_token = result.scalar_one_or_none()
                
                if not stored_token:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Refresh token not found or revoked"
                    )

                user = await session.get(User, token_data.sub)
                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account no longer exists.",
                    )
                if str(user.status).upper() != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This account is temporarily disabled. Please contact an administrator.",
                    )
                
                # Generate new access token
                issued_at = datetime.now(timezone.utc)
                new_access_token = jwt.encode(
                    {
                        "sub": token_data.sub,
                        "exp": issued_at + timedelta(
                            minutes=auth_config.ACCESS_TOKEN_EXPIRE_MINUTES
                        ),
                        "iat": issued_at,
                        "type": "access",
                        "jti": str(uuid.uuid4())
                    },
                    auth_config.JWT_SECRET_KEY,
                    algorithm=auth_config.JWT_ALGORITHM
                )
                
                return {"access_token": new_access_token, "token_type": "bearer"}
            
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token expired"
            )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def logout(self, refresh_token: str, user_id: UUID | None = None) -> None:
        async with get_session() as session:
            # Revoke refresh token
            conditions = [RefreshToken.token == refresh_token]
            if user_id is not None:
                conditions.append(RefreshToken.user_id == user_id)
            stmt = select(RefreshToken).where(and_(*conditions))
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            
            if token:
                token.revoked = True
                token.revoked_at = datetime.now(timezone.utc)
                await session.commit()
    
    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str
    ) -> None:
        async with get_session() as session:
            # Get user
            stmt = select(User).where(User.id == user_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            
            if not user:
                raise ValidationError("User not found")
            
            # Verify current password
            if not self.verify_password(current_password, user.hashed_password):
                raise AuthenticationError("Current password is incorrect")
            
            # Update password
            user.hashed_password = self.hash_password(new_password)
            await session.commit()
            
            # Revoke all refresh tokens for this user
            stmt = select(RefreshToken).where(
                and_(
                    RefreshToken.user_id == user_id,
                    RefreshToken.revoked == False
                )
            )
            result = await session.execute(stmt)
            tokens = result.scalars().all()
            
            for token in tokens:
                token.revoked = True
                token.revoked_at = datetime.now(timezone.utc)
            
            await session.commit()

    async def get_token_from_request(self, request: Request) -> Optional[str]:
        """
        Extract token from Authorization header
        Replaces Auth0's header extraction
        """
        authorization = request.headers.get("Authorization")
        if not authorization:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authorization header missing",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Extract token from "Bearer <token>"
        parts = authorization.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header format. Expected 'Bearer <token>'",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return parts[1]
    
    async def verify_token(self, token: str) -> dict:
        """
        Verify token - replaces Auth0's verify_token
        """
        return await self.token_verifier.verify(token)
    
    async def get_user_id_from_token(self, token: dict) -> dict:
        """
        Extract user ID from verified token payload as a UUID.
        """
        user_id = token.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token does not contain user ID (sub claim)"
            )

        try:
            uuid_obj = UUID(str(user_id))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token contains an invalid user ID",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return {"user_id": uuid_obj}



def validate_token(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        request: Request = kwargs.get("request")
        if not request:
            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

        if not request:
            raise HTTPException(status_code=400, detail="Request object not found")

        try:
            token_repo = TokenRepository()
            token = await token_repo.get_token_from_request(request)
            token_payload = await token_repo.verify_token(token)
            if token_payload.get("type") != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="An access token is required.",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            user_data = await token_repo.get_user_id_from_token(token_payload)
            async with get_session() as session:
                user = await session.get(User, user_data["user_id"])
                if user is None:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="User account no longer exists.",
                    )
                if str(user.status).upper() != "ACTIVE":
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="This account is temporarily disabled. Please contact an administrator.",
                    )
            kwargs["user_id"] = user_data["user_id"]
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication failed",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Keep endpoint and database errors out of the authentication failure path.
        return await func(*args, **kwargs)
    
    return wrapper


async def get_optional_user_id(request: Request) -> UUID | None:
    """Authenticate an optional bearer token without treating guests as users."""
    authorization = request.headers.get("Authorization")
    if not authorization:
        return None
    token_repo = TokenRepository()
    token = await token_repo.get_token_from_request(request)
    payload = await token_repo.verify_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="An access token is required.")
    user_data = await token_repo.get_user_id_from_token(payload)
    async with get_session() as session:
        user = await session.get(User, user_data["user_id"])
        if user is None:
            raise HTTPException(status_code=401, detail="User account no longer exists.")
        if str(user.status).upper() != "ACTIVE":
            raise HTTPException(status_code=403, detail="This account is inactive.")
    return user_data["user_id"]



def validate_headers(authorization):
    scheme, token = get_authorization_scheme_param(authorization)
    try:
        headers = Header(
            token=HTTPBearer(scheme_name=scheme.lower(), bearerFormat=token),
        )
        return headers
    except ValidationError as e:
        raise Exception(e.errors())


async def get_user_id(request: Request):
    token = await TokenRepository().get_token_from_request(request)
    payload = await TokenRepository().verify_token(token=token)
    return payload["user_id"]


async def get_agent_id(request: Request):
    token = await TokenRepository().get_token_from_request(request)
    payload = await TokenRepository().verify_token(token=token)
    return payload["agent_id"]

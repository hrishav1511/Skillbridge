from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta, timezone
import uuid
import jwt
import bcrypt
from typing import Optional, Dict, Any
from fastapi import Request, HTTPException, status

from skillbridge.database.db.database import get_session
from skillbridge.database.models.sqlalchemy.refresh_tokens import RefreshToken
from skillbridge.database.models.sqlalchemy.users import User

from .config import auth_config
from skillbridge.api.schemas.token import TokenPayload
from skillbridge.exceptions import AuthenticationError, NotFoundError

class AuthService:
    
    
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
        request: Request
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
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    
    async def logout(self, refresh_token: str) -> None:
        async with get_session() as session:
        
            # Revoke refresh token
            stmt = select(RefreshToken).where(
                RefreshToken.token == refresh_token
            )
            result = await session.execute(stmt)
            token = result.scalar_one_or_none()
            
            if token:
                token.revoked = True
                token.revoked_at = datetime.utcnow()
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
                raise NotFoundError("User not found")
            
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
                token.revoked_at = datetime.utcnow()
            
            await session.commit()

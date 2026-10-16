# auth/token_verifier.py
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTClaimsError, JWTError
from fastapi import HTTPException, status
from typing import Optional, Dict, Any
from datetime import datetime
from skillbridge.api.repositories.auth.config import auth_config
class TokenVerifier:
    """
    Self-contained JWT token verification
    No external dependencies (Auth0, JWKS, etc.)
    """
    
    def __init__(self):
        self.secret_key = auth_config.JWT_SECRET_KEY
        self.algorithm = auth_config.JWT_ALGORITHM  # "HS256"
        self.audience = auth_config.JWT_AUDIENCE  # Optional
        self.issuer = auth_config.JWT_ISSUER  # Optional
    
    async def verify(
        self,
        token: str,
        required_scopes: Optional[list] = None,
    ) -> Dict[str, Any]:
        """
        Verify JWT token - replaces Auth0's verify method
        
        Args:
            token: JWT token string
            required_scopes: Optional list of required scopes
            
        Returns:
            Decoded token payload
            
        Raises:
            HTTPException: If token is invalid
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No token provided",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={
                    "require": ["exp", "iat", "sub"],  # Required claims
                    "verify_signature": True,
                    "verify_exp": True,
                }
            )
            
            # Optional: Verify scopes
            if required_scopes:
                self._verify_scopes(payload, required_scopes)
            
            return payload
            
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTClaimsError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token issuer",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def _verify_scopes(self, payload: dict, required_scopes: list):
        """
        Verify token scopes (matching Auth0's behavior)
        """
        token_scopes = payload.get("scope", "")
        if not token_scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No scopes found in token"
            )
        
        token_scopes_list = token_scopes.split(" ")
        
        for scope in required_scopes:
            if scope not in token_scopes_list:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f'Missing required scope: "{scope}"'
                )

# backend/app/core/auth.py
from datetime import datetime, timedelta
import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import httpx
from app_logger import logger
from app.models.user import UserDocument
from fastapi.responses import JSONResponse

class TokenExpiredError(Exception):
    pass

JWT_SECRET = os.getenv("JWT_SECRET", "codesense-super-secret-key-change-me-in-production-123456")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

security = HTTPBearer(auto_error=False)

def create_access_token(user_id: str, email: str) -> str:
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {
        "sub": user_id,
        "email": email,
        "type": "access",
        "exp": expire
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire
    }
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str, token_type: str = "access") -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != token_type:
            logger.warning(f"Invalid token type. Expected {token_type}, got {payload.get('type')}")
            return None
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning(f"Expired {token_type} token signature")
        raise TokenExpiredError()
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid {token_type} token signature: {e}")
        return None

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import get_settings

async def verify_google_token(token: str) -> Optional[dict]:
    """Verify Google OAuth token against Google API with client ID audience validation."""
    settings = get_settings()
    if not settings.GOOGLE_CLIENT_ID:
        logger.error("GOOGLE_CLIENT_ID is not configured in settings.")
        return None
    try:
        # Validate signature and audience using google-auth official verification library
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception as e:
        logger.error(f"Google token verification failed: {e}")
        return None

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> UserDocument:
    """FastAPI Dependency to retrieve authenticated user."""
    if not credentials:
        logger.warning("Auth failed: Missing token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization credentials"
        )
    
    token = credentials.credentials
    try:
        payload = verify_token(token, "access")
    except TokenExpiredError:
        logger.warning("Auth failed: Expired token")
        raise

    if not payload:
        logger.warning("Auth failed: Invalid signature")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token"
        )
        
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("Auth failed: Invalid signature (No User ID)")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User ID not found in token"
        )
        
    user = await UserDocument.get(user_id)
    if not user:
        logger.warning(f"Auth failed: User not found ({user_id})")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )
        
    return user

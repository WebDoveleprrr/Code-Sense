# backend/app/api/v1/auth.py
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel
from app.core.auth import (
    verify_google_token,
    create_access_token,
    create_refresh_token,
    verify_token,
    get_current_user
)
from app.models.user import UserDocument

router = APIRouter()

class GoogleLoginRequest(BaseModel):
    id_token: str

class TokenRefreshRequest(BaseModel):
    refresh_token: str

class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    user: dict

@router.post("/google", response_model=LoginResponse)
async def google_login(payload: GoogleLoginRequest):
    """
    Authenticate a user via Google Sign-In id_token.
    Create user record in MongoDB if new.
    """
    # 1. Verify token with Google APIs
    user_info = await verify_google_token(payload.id_token)
    if not user_info:
        # For development / testing purposes, check if the token is a mock/test token and settings.is_development is true
        from app.core.config import get_settings
        settings = get_settings()
        if settings.is_development and payload.id_token.startswith("mock_token_"):
            email = f"{payload.id_token.replace('mock_token_', '')}@example.com"
            user_info = {
                "email": email,
                "name": email.split("@")[0].capitalize(),
                "picture": None
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google token verification failed"
            )

    email = user_info.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email field missing from Google token claims"
        )

    # 2. Get or create user record
    user = await UserDocument.find_one(UserDocument.email == email)
    if not user:
        user = UserDocument(
            email=email,
            name=user_info.get("name", email.split("@")[0]),
            picture=user_info.get("picture")
        )
        await user.insert()
        
    # 3. Generate tokens
    user_id_str = str(user.id)
    access_token = create_access_token(user_id_str, email)
    refresh_token = create_refresh_token(user_id_str)
    
    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user={
            "id": user_id_str,
            "email": user.email,
            "name": user.name,
            "picture": user.picture
        }
    )

@router.post("/refresh")
async def refresh_tokens(payload: TokenRefreshRequest):
    """
    Generate a new access token using a valid refresh token.
    """
    payload_data = verify_token(payload.refresh_token, "refresh")
    if not payload_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
        
    user_id = payload_data.get("sub")
    user = await UserDocument.get(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found"
        )
        
    new_access_token = create_access_token(str(user.id), user.email)
    new_refresh_token = create_refresh_token(str(user.id))
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "user": {
            "id": str(user.id),
            "email": user.email,
            "name": user.name,
            "picture": user.picture
        }
    }

@router.get("/me")
async def get_me(current_user: UserDocument = Depends(get_current_user)):
    """
    Get current logged in user details.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "name": current_user.name,
        "picture": current_user.picture
    }

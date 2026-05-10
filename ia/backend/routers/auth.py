"""
StudyFlow AI - Auth Router
Registration, login, Google OAuth, profile management.
"""
import json
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db
from backend.models.user import User
from backend.services.auth_service import (
    hash_password, verify_password, create_access_token,
    decode_access_token, verify_google_token,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


# --- Pydantic Schemas ---
class RegisterRequest(BaseModel):
    email: str
    username: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    token: str

class ProfileUpdateRequest(BaseModel):
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Optional[str] = None


# --- Auth Dependency ---
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    """Extract and validate the current user from the Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token = auth_header.split(" ", 1)[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    return user


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# --- Endpoints ---
@router.post("/register")
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user with email and password."""
    # Check if email exists
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Check username length
    if len(req.username) < 2:
        raise HTTPException(status_code=400, detail="Username must be at least 2 characters")
    if len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
    
    user = User(
        email=req.email,
        username=req.username,
        hashed_password=hash_password(req.password),
        auth_provider="local",
    )
    db.add(user)
    await db.flush()
    
    token = create_access_token(user.id, user.email, user.role)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "preferences": json.loads(user.preferences or "{}"),
        }
    }


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    
    # Update last login
    user.last_login = datetime.now(timezone.utc)
    
    token = create_access_token(user.id, user.email, user.role)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "preferences": json.loads(user.preferences or "{}"),
        }
    }


@router.post("/google")
async def google_auth(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    """Authenticate with Google OAuth."""
    google_user = await verify_google_token(req.token)
    if not google_user:
        raise HTTPException(status_code=401, detail="Invalid Google token")
    
    # Check if user exists by google_id
    result = await db.execute(select(User).where(User.google_id == google_user["google_id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        # Check by email
        result = await db.execute(select(User).where(User.email == google_user["email"]))
        user = result.scalar_one_or_none()
        
        if user:
            # Link Google account to existing user
            user.google_id = google_user["google_id"]
            user.avatar_url = google_user.get("avatar")
        else:
            # Create new user
            user = User(
                email=google_user["email"],
                username=google_user["name"],
                google_id=google_user["google_id"],
                avatar_url=google_user.get("avatar"),
                auth_provider="google",
            )
            db.add(user)
    
    user.last_login = datetime.now(timezone.utc)
    await db.flush()
    
    token = create_access_token(user.id, user.email, user.role)
    
    return {
        "token": token,
        "user": {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "avatar_url": user.avatar_url,
            "preferences": json.loads(user.preferences or "{}"),
        }
    }


@router.get("/me")
async def get_me(user: User = Depends(get_current_user)):
    """Get current user info."""
    return {
        "id": user.id,
        "email": user.email,
        "username": user.username,
        "role": user.role,
        "avatar_url": user.avatar_url,
        "auth_provider": user.auth_provider,
        "preferences": json.loads(user.preferences or "{}"),
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.put("/profile")
async def update_profile(
    req: ProfileUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update user profile."""
    if req.username is not None:
        user.username = req.username
    if req.avatar_url is not None:
        user.avatar_url = req.avatar_url
    if req.preferences is not None:
        user.preferences = req.preferences
    
    return {"message": "Profile updated", "username": user.username}

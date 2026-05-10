"""
StudyFlow AI - User Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Boolean, Text
from backend.models.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google OAuth users
    avatar_url = Column(String(500), nullable=True)
    role = Column(String(20), default="user")  # user, admin
    auth_provider = Column(String(20), default="local")  # local, google
    google_id = Column(String(255), nullable=True, unique=True)
    preferences = Column(Text, nullable=True, default='{"theme":"dark","language":"en"}')
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_login = Column(DateTime, nullable=True)

"""
StudyFlow AI - Uploaded File Model
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Integer, Text, ForeignKey
from backend.models.database import Base


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_name = Column(String(500), nullable=False)
    stored_name = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String(100), nullable=True)
    extracted_text = Column(Text, nullable=True)
    subject = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    is_indexed = Column(Integer, default=0)  # 0=no, 1=yes
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

"""
StudyFlow AI - Conversations Router
"""
import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import get_db
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.uploaded_file import UploadedFile
from backend.services.rag_service import delete_conversation_index
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/conversations", tags=["conversations"])

class ConversationCreate(BaseModel):
    title: Optional[str] = "New Conversation"

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    folder: Optional[str] = None
    is_archived: Optional[bool] = None

@router.get("")
async def list_conversations(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.user_id == user.id).order_by(Conversation.updated_at.desc()))
    conversations = result.scalars().all()
    conv_list = []
    for conv in conversations:
        msg_count_result = await db.execute(select(func.count(Message.id)).where(Message.conversation_id == conv.id))
        msg_count = msg_count_result.scalar() or 0
        last_msg_result = await db.execute(select(Message).where(Message.conversation_id == conv.id, Message.role == "user").order_by(Message.created_at.desc()).limit(1))
        last_msg = last_msg_result.scalar_one_or_none()
        conv_list.append({
            "id": conv.id, "title": conv.title, "folder": conv.folder,
            "is_archived": conv.is_archived, "message_count": msg_count,
            "last_message": last_msg.content[:100] if last_msg else None,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        })
    return {"conversations": conv_list}

@router.post("")
async def create_conversation(req: ConversationCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    conv = Conversation(user_id=user.id, title=req.title or "New Conversation")
    db.add(conv)
    await db.flush()
    return {"id": conv.id, "title": conv.title, "created_at": conv.created_at.isoformat() if conv.created_at else None}

@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    msg_result = await db.execute(select(Message).where(Message.conversation_id == conversation_id).order_by(Message.created_at))
    messages = msg_result.scalars().all()
    file_result = await db.execute(select(UploadedFile).where(UploadedFile.conversation_id == conversation_id).order_by(UploadedFile.created_at))
    files = file_result.scalars().all()
    return {
        "id": conv.id, "title": conv.title, "folder": conv.folder, "is_archived": conv.is_archived,
        "created_at": conv.created_at.isoformat() if conv.created_at else None,
        "messages": [{"id": m.id, "role": m.role, "content": m.content, "files_metadata": json.loads(m.files_metadata) if m.files_metadata else None, "created_at": m.created_at.isoformat() if m.created_at else None} for m in messages],
        "files": [{"id": f.id, "name": f.original_name, "type": f.file_type, "size": f.file_size, "created_at": f.created_at.isoformat() if f.created_at else None} for f in files],
    }

@router.put("/{conversation_id}")
async def update_conversation(conversation_id: str, req: ConversationUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if req.title is not None: conv.title = req.title
    if req.folder is not None: conv.folder = req.folder
    if req.is_archived is not None: conv.is_archived = req.is_archived
    return {"message": "Updated", "title": conv.title}

@router.delete("/{conversation_id}")
async def delete_conversation(conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    await db.execute(delete(Message).where(Message.conversation_id == conversation_id))
    await db.execute(delete(UploadedFile).where(UploadedFile.conversation_id == conversation_id))
    await delete_conversation_index(conversation_id)
    await db.delete(conv)
    return {"message": "Deleted"}

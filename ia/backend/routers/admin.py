"""
StudyFlow AI - Admin Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import get_db
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.models.uploaded_file import UploadedFile
from backend.routers.auth import get_admin_user

router = APIRouter(prefix="/api/admin", tags=["admin"])

@router.get("/stats")
async def get_stats(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    users = (await db.execute(select(func.count(User.id)))).scalar() or 0
    convs = (await db.execute(select(func.count(Conversation.id)))).scalar() or 0
    msgs = (await db.execute(select(func.count(Message.id)))).scalar() or 0
    files = (await db.execute(select(func.count(UploadedFile.id)))).scalar() or 0
    tokens = (await db.execute(select(func.sum(Message.tokens_used)))).scalar() or 0
    storage = (await db.execute(select(func.sum(UploadedFile.file_size)))).scalar() or 0
    return {"users": users, "conversations": convs, "messages": msgs, "files": files, "total_tokens": tokens, "storage_bytes": storage}

@router.get("/users")
async def list_users(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    user_list = []
    for u in users:
        msg_count = (await db.execute(select(func.count(Message.id)).join(Conversation, Message.conversation_id == Conversation.id).where(Conversation.user_id == u.id))).scalar() or 0
        user_list.append({"id": u.id, "email": u.email, "username": u.username, "role": u.role, "auth_provider": u.auth_provider, "is_active": u.is_active, "message_count": msg_count, "created_at": u.created_at.isoformat() if u.created_at else None, "last_login": u.last_login.isoformat() if u.last_login else None})
    return {"users": user_list}

@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    if user_id == admin.id:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = False
    return {"message": "User deactivated"}

@router.get("/files")
async def list_all_files(admin: User = Depends(get_admin_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UploadedFile).order_by(UploadedFile.created_at.desc()).limit(100))
    files = result.scalars().all()
    return {"files": [{"id": f.id, "name": f.original_name, "type": f.file_type, "size": f.file_size, "user_id": f.user_id, "conversation_id": f.conversation_id, "indexed": f.is_indexed == 1, "created_at": f.created_at.isoformat() if f.created_at else None} for f in files]}

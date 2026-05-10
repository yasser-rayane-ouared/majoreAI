"""
StudyFlow AI - File Upload Router
"""
import os, uuid, json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
from backend.models.database import get_db
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.uploaded_file import UploadedFile as UploadedFileModel
from backend.services.file_processor import extract_text_from_file
from backend.services.rag_service import index_document
from backend.services.ai_service import analyze_document_content
from backend.routers.auth import get_current_user
from typing import List

router = APIRouter(prefix="/api/files", tags=["files"])

@router.post("/upload")
async def upload_files(
    conversation_id: str = Form(...),
    files: List[UploadFile] = File(...),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    uploaded = []
    for file in files:
        ext = Path(file.filename or "").suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            uploaded.append({"name": file.filename, "error": f"File type {ext} not allowed"})
            continue

        file_id = str(uuid.uuid4())
        stored_name = f"{file_id}{ext}"
        conv_dir = UPLOAD_DIR / conversation_id
        conv_dir.mkdir(parents=True, exist_ok=True)
        file_path = conv_dir / stored_name

        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            uploaded.append({"name": file.filename, "error": "File too large"})
            continue

        with open(file_path, "wb") as f:
            f.write(content)

        # Extract text
        extracted = await extract_text_from_file(str(file_path), file.filename or "", file.content_type or "")

        # Analyze content (Smart Upload)
        analysis = {"subject": "General", "summary": "No summary available.", "quality_warning": None}
        if extracted["text"].strip():
            analysis = await analyze_document_content(extracted["text"])

        # Save to DB
        db_file = UploadedFileModel(
            id=file_id, conversation_id=conversation_id, user_id=user.id,
            original_name=file.filename or "unknown", stored_name=stored_name,
            file_type=extracted["file_type"], file_size=len(content),
            mime_type=file.content_type, extracted_text=extracted["text"][:50000],
            subject=analysis.get("subject", "General"), 
            summary=analysis.get("summary", ""),
        )
        db.add(db_file)

        # Index in ChromaDB for RAG
        if extracted["text"] and not extracted.get("error"):
            indexed = await index_document(conversation_id, file.filename or "", extracted["text"], file_id)
            db_file.is_indexed = 1 if indexed else 0

        uploaded.append({
            "id": file_id, "name": file.filename, "type": extracted["file_type"],
            "size": len(content), "indexed": db_file.is_indexed == 1,
        })

    return {"files": uploaded}

@router.get("/{conversation_id}")
async def list_files(conversation_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user.id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")
    file_result = await db.execute(select(UploadedFileModel).where(UploadedFileModel.conversation_id == conversation_id).order_by(UploadedFileModel.created_at))
    files = file_result.scalars().all()
    return {"files": [
        {
            "id": f.id, "name": f.original_name, "type": f.file_type, 
            "size": f.file_size, "indexed": f.is_indexed == 1, 
            "subject": f.subject, "summary": f.summary,
            "created_at": f.created_at.isoformat() if f.created_at else None
        } for f in files
    ]}

@router.get("/content/{file_id}")
async def get_file_content(file_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UploadedFileModel).where(UploadedFileModel.id == file_id, UploadedFileModel.user_id == user.id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    return {"text": f.extracted_text or "[No text content]"}

@router.delete("/{file_id}")
async def delete_file(file_id: str, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(UploadedFileModel).where(UploadedFileModel.id == file_id, UploadedFileModel.user_id == user.id))
    f = result.scalar_one_or_none()
    if not f:
        raise HTTPException(status_code=404, detail="File not found")
    file_path = UPLOAD_DIR / f.conversation_id / f.stored_name
    if file_path.exists():
        os.remove(file_path)
    await db.delete(f)
    return {"message": "File deleted"}

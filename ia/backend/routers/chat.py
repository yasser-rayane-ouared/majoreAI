"""
StudyFlow AI - Chat Router
WebSocket streaming chat + REST fallback.
"""
import json
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.database import get_db, async_session
from backend.models.user import User
from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.services.ai_service import chat_stream, chat_complete, generate_title
from backend.services.rag_service import search_documents, build_rag_context
from backend.services.auth_service import decode_access_token
from backend.routers.auth import get_current_user

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None


@router.post("")
async def chat_rest(
    req: ChatRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """REST endpoint for chat (non-streaming fallback)."""
    conversation_id = req.conversation_id
    
    # Create conversation if needed
    if not conversation_id:
        conv = Conversation(user_id=user.id, title="New Conversation")
        db.add(conv)
        await db.flush()
        conversation_id = conv.id
    else:
        # Verify ownership
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.user_id == user.id,
            )
        )
        conv = result.scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
    
    # Get conversation history
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
        .limit(20)
    )
    history_msgs = result.scalars().all()
    
    # Build messages for AI
    messages = []
    for msg in history_msgs:
        messages.append({"role": msg.role, "content": msg.content})
    
    # RAG: Search uploaded documents
    rag_context = ""
    rag_results = await search_documents(conversation_id, req.message)
    if rag_results:
        rag_context = build_rag_context(rag_results)
    
    # Add user message with RAG context
    user_content = req.message
    if rag_context:
        user_content = req.message + rag_context
    messages.append({"role": "user", "content": user_content})
    
    # Save user message
    user_msg = Message(
        conversation_id=conversation_id,
        role="user",
        content=req.message,
    )
    db.add(user_msg)
    
    # Get AI response
    result = await chat_complete(messages, model=req.model)
    
    # Save assistant message
    assistant_msg = Message(
        conversation_id=conversation_id,
        role="assistant",
        content=result["content"],
        tokens_used=result["tokens"],
    )
    db.add(assistant_msg)
    
    # Generate title for new conversations
    if len(history_msgs) == 0:
        title = await generate_title(req.message)
        conv = await db.get(Conversation, conversation_id)
        if conv:
            conv.title = title
    
    return {
        "conversation_id": conversation_id,
        "message": result["content"],
        "tokens_used": result["tokens"],
    }


@router.websocket("/ws/{conversation_id}")
async def chat_websocket(websocket: WebSocket, conversation_id: str):
    """WebSocket endpoint for real-time streaming chat."""
    await websocket.accept()
    
    # Authenticate via query param or first message
    token = websocket.query_params.get("token", "")
    payload = decode_access_token(token)
    if not payload:
        await websocket.send_json({"type": "error", "content": "Authentication required"})
        await websocket.close(code=4001)
        return
    
    user_id = payload["sub"]
    
    try:
        while True:
            data = await websocket.receive_json()
            message_text = data.get("message", "")
            
            if not message_text.strip():
                continue
            
            async with async_session() as db:
                # Verify conversation ownership
                result = await db.execute(
                    select(Conversation).where(
                        Conversation.id == conversation_id,
                        Conversation.user_id == user_id,
                    )
                )
                conv = result.scalar_one_or_none()
                if not conv:
                    await websocket.send_json({"type": "error", "content": "Conversation not found"})
                    continue
                
                # Get history
                result = await db.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation_id)
                    .order_by(Message.created_at)
                    .limit(20)
                )
                history_msgs = result.scalars().all()
                
                # Build messages
                messages = [{"role": m.role, "content": m.content} for m in history_msgs]
                
                # RAG context
                rag_context = ""
                rag_results = await search_documents(conversation_id, message_text)
                if rag_results:
                    rag_context = build_rag_context(rag_results)
                
                user_content = message_text + rag_context if rag_context else message_text
                messages.append({"role": "user", "content": user_content})
                
                # Save user message
                user_msg = Message(
                    conversation_id=conversation_id,
                    role="user",
                    content=message_text,
                )
                db.add(user_msg)
                await db.commit()
                
                # Stream AI response
                full_response = ""
                await websocket.send_json({"type": "stream_start"})
                
                chat_mode = data.get("mode", "study")
                async for token in chat_stream(messages, model=data.get("model"), mode=chat_mode):
                    full_response += token
                    await websocket.send_json({
                        "type": "stream_token",
                        "content": token,
                    })
                
                await websocket.send_json({
                    "type": "stream_end",
                    "content": full_response,
                })
                
                # Save assistant message
                assistant_msg = Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_response,
                )
                db.add(assistant_msg)
                
                # Generate title if first message
                if len(history_msgs) == 0:
                    title = await generate_title(message_text)
                    conv.title = title
                    await websocket.send_json({
                        "type": "title_update",
                        "title": title,
                    })
                
                await db.commit()
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"type": "error", "content": str(e)})
        except Exception:
            pass

"""
StudyFlow AI - Lightweight RAG Service (No ChromaDB)
A fallback implementation for environments without ChromaDB support.
"""
import uuid
import re
from typing import List, Dict
from backend.config import CHUNK_SIZE, CHUNK_OVERLAP, TOP_K_RESULTS
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.database import async_session
from backend.models.uploaded_file import UploadedFile

# In-memory document index (would use SQLite or vector DB in production)
_document_index = {}


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """Split text into overlapping chunks."""
    chunk_size = chunk_size or CHUNK_SIZE
    overlap = overlap or CHUNK_OVERLAP
    
    if not text or len(text) < 50:
        return [text] if text else []
    
    chunks = []
    paragraphs = text.split("\n\n")
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) < chunk_size:
            current_chunk += para + "\n\n"
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            if len(para) > chunk_size:
                sentences = para.replace(". ", ".\n").split("\n")
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) < chunk_size:
                        current_chunk += sent + " "
                    else:
                        if current_chunk.strip():
                            chunks.append(current_chunk.strip())
                        current_chunk = sent + " "
            else:
                current_chunk = para + "\n\n"
    
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text[:chunk_size]]


async def index_document(conversation_id: str, file_name: str, text: str, file_id: str = None) -> bool:
    """Index a document's text into memory (fallback RAG)."""
    if conversation_id not in _document_index:
        _document_index[conversation_id] = []
        
    chunks = chunk_text(text)
    if not chunks:
        return False
    
    for i, chunk in enumerate(chunks):
        _document_index[conversation_id].append({
            "id": f"{file_id or uuid.uuid4().hex}_{i}",
            "file_name": file_name,
            "text": chunk,
            "chunk_index": i
        })
        
    return True


async def search_documents(conversation_id: str, query: str, top_k: int = None) -> List[Dict]:
    """Simple keyword-based search (BM25-lite) for fallback RAG."""
    top_k = top_k or TOP_K_RESULTS
    
    # Check memory cache first
    docs = _document_index.get(conversation_id, [])
    
    # If not in memory but might be in DB, load them
    if not docs:
        async with async_session() as db:
            result = await db.execute(
                select(UploadedFile).where(UploadedFile.conversation_id == conversation_id)
            )
            files = result.scalars().all()
            for f in files:
                if f.extracted_text:
                    await index_document(conversation_id, f.original_name, f.extracted_text, f.id)
            
            docs = _document_index.get(conversation_id, [])
            
    if not docs:
        return []
        
    # Very simple keyword matching algorithm
    # 1. Extract alphanumeric keywords from query
    keywords = set(re.findall(r'\b\w{3,}\b', query.lower()))
    
    if not keywords:
        # If query has no real keywords, just return the first few chunks
        return docs[:top_k]
        
    # 2. Score each document chunk
    scored_docs = []
    for doc in docs:
        text_lower = doc["text"].lower()
        score = 0
        for kw in keywords:
            # Count occurrences
            count = text_lower.count(kw)
            if count > 0:
                score += count * len(kw)  # Longer keywords worth more
                
        if score > 0:
            scored_doc = doc.copy()
            scored_doc["relevance"] = score
            scored_docs.append(scored_doc)
            
    # Sort by score descending
    scored_docs.sort(key=lambda x: x["relevance"], reverse=True)
    
    return scored_docs[:top_k]


async def delete_conversation_index(conversation_id: str) -> bool:
    """Delete all indexed documents for a conversation."""
    if conversation_id in _document_index:
        del _document_index[conversation_id]
        return True
    return False


def build_rag_context(search_results: List[Dict]) -> str:
    """Build a context string from search results."""
    if not search_results:
        return ""
    
    context_parts = []
    seen_files = set()
    
    for result in search_results:
        file_name = result["file_name"]
        if file_name not in seen_files:
            seen_files.add(file_name)
            context_parts.append(f"\n📄 **From: {file_name}**")
        context_parts.append(result["text"])
    
    context = "\n\n".join(context_parts)
    return f"\n\n---\n**📚 Relevant content from your uploaded files:**\n{context}\n---\n"

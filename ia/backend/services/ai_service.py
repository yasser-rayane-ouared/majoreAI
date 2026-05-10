"""
StudyFlow AI - AI Service
Unified interface for OpenAI API with streaming support.
"""
import json
from typing import AsyncGenerator, Optional, List, Dict
from openai import AsyncOpenAI
from backend.config import OPENAI_API_KEY, AI_MODEL, OPENAI_BASE_URL

# Initialize OpenAI client
client = AsyncOpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_BASE_URL
) if OPENAI_API_KEY else None

SYSTEM_PROMPT = """You are KHABACH AI, a premium educational assistant specialized in:

🎓 **Education & Studying**: Explain lessons clearly, generate quizzes, create flashcards, solve exercises step-by-step, create study plans, simulate exams, and analyze academic materials.

💻 **Coding & Programming**: Debug code, explain algorithms, write clean solutions, review code quality, teach programming concepts with examples, and help with any programming language.

💼 **Business & Entrepreneurship**: Write business plans, marketing strategies, financial analysis, pitch decks, market research, and startup guidance.

Your capabilities:
- Analyze uploaded documents (PDF, DOCX, PPTX, CSV, images, code files)
- Generate quizzes, exams, and practice exercises from uploaded materials
- Create summaries and flashcards from study materials
- Translate content between Arabic, English, and French
- Solve math, science, and engineering problems step-by-step
- Write and debug code in any programming language
- Generate study plans and learning roadmaps

Guidelines:
1. Use rich markdown formatting: headers, bold, lists, code blocks, tables
2. Always explain step-by-step when solving problems
3. When reviewing code, provide the corrected version with explanations
4. Be thorough but concise - use bullet points for clarity
5. For quizzes, include answers with explanations
6. Support multilingual responses (Arabic, English, French)
7. When given uploaded file content, reference specific parts in your answers
"""

CHALLENGE_MODE_PROMPT = """You are KHABACH AI in **Challenge Mode**. 
Your goal is to act as a strict but encouraging teacher.
Instead of answering questions, you MUST ask the user questions based on their uploaded materials or the topic at hand.
1. Start by assessing the user's level.
2. Ask one clear, challenging question at a time.
3. Wait for the user's answer, then provide feedback (correct/incorrect and why).
4. Increase the difficulty if they answer correctly; provide hints if they struggle.
5. Keep track of their "Score" and encourage them to reach the next level.
"""

async def analyze_document_content(text: str) -> Dict:
    """Analyze document content to detect subject, summary, and quality."""
    if not client or not text.strip():
        return {"subject": "General", "summary": "No content to analyze.", "quality": "N/A"}
    
    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "You are a document analyzer. Analyze the text and return a JSON object with: 'subject' (2-3 words), 'summary' (max 2 sentences), and 'quality_warning' (null or a short warning if content is low quality or truncated)."},
                {"role": "user", "content": text[:4000]} # Limit for efficiency
            ],
            response_format={ "type": "json_object" },
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"Analysis error: {e}")
        return {"subject": "General", "summary": "Summary unavailable.", "quality_warning": None}



async def chat_stream(
    messages: List[Dict[str, str]],
    model: str = None,
    mode: str = "study",
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> AsyncGenerator[str, None]:
    """Stream chat responses token by token."""
    if not client:
        yield "⚠️ OpenAI API key not configured. Please add your API key to the .env file."
        return

    use_model = model or AI_MODEL
    
    # Prepend system message based on mode
    sys_prompt = CHALLENGE_MODE_PROMPT if mode == "challenge" else SYSTEM_PROMPT
    full_messages = [{"role": "system", "content": sys_prompt}] + messages

    try:
        stream = await client.chat.completions.create(
            model=use_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    except Exception as e:
        error_msg = str(e)
        if "api_key" in error_msg.lower() or "authentication" in error_msg.lower():
            yield f"\n\n⚠️ **API Key Error**: Please check your OpenAI API key in the .env file."
        elif "model" in error_msg.lower():
            yield f"\n\n⚠️ **Model Error**: The model `{use_model}` is not available. Try changing AI_MODEL in .env."
        else:
            yield f"\n\n⚠️ **Error**: {error_msg}"


async def chat_complete(
    messages: List[Dict[str, str]],
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
) -> dict:
    """Get a complete (non-streaming) chat response."""
    if not client:
        return {"content": "⚠️ OpenAI API key not configured.", "tokens": 0}

    use_model = model or AI_MODEL
    full_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages

    try:
        response = await client.chat.completions.create(
            model=use_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return {
            "content": response.choices[0].message.content,
            "tokens": response.usage.total_tokens if response.usage else 0,
        }
    except Exception as e:
        return {"content": f"⚠️ Error: {str(e)}", "tokens": 0}


async def generate_title(first_message: str) -> str:
    """Generate a short conversation title from the first message."""
    if not client:
        return first_message[:50] + "..." if len(first_message) > 50 else first_message
    
    try:
        response = await client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": "Generate a very short title (max 6 words) for a conversation that starts with the following message. Reply with ONLY the title, no quotes or punctuation."},
                {"role": "user", "content": first_message[:500]},
            ],
            temperature=0.5,
            max_tokens=20,
        )
        title = response.choices[0].message.content.strip().strip('"').strip("'")
        return title[:60]
    except Exception as e:
        print(f"Failed to generate title: {e}")
        return first_message[:40] + ("..." if len(first_message) > 40 else "")


async def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """Generate embeddings for text chunks using OpenAI."""
    if not client:
        return []
    
    try:
        from backend.config import EMBEDDING_MODEL
        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=texts,
        )
        return [item.embedding for item in response.data]
    except Exception as e:
        print(f"Embedding error: {e}")
        return []

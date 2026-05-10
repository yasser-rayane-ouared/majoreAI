# StudyFlow AI 🎓

A premium AI-powered educational platform for studying, coding, and business assistance.

## Features

- 🤖 **AI Chat** with real-time streaming (WebSocket)
- 📁 **Unlimited file uploads** (PDF, DOCX, PPTX, CSV, images, code, ZIP)
- 🔍 **RAG Pipeline** - AI answers based on your uploaded materials
- 🌙 **Dark/Light mode** with smooth transitions
- 🔐 **Authentication** (email/password + Google OAuth)
- 📊 **Admin dashboard** with analytics
- 🎤 **Voice input/output**
- 📥 **Export chats** to Markdown
- 📱 **Fully responsive** mobile design

## Quick Start

### 1. Prerequisites

- Python 3.10+
- OpenAI API key

### 2. Install Dependencies

```bash
cd c:\Users\LENOVO\OneDrive\Desktop\ia
pip install -r backend/requirements.txt
```

### 3. Configure Environment

Edit `.env` and add your OpenAI API key:

```
OPENAI_API_KEY=sk-your-key-here
```

### 4. Run the Server

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Open in Browser

Go to [http://localhost:8000](http://localhost:8000)

### 6. Create an Account

Register at `/register`, then start chatting!

### 7. Make Yourself Admin (Optional)

After registering, to get admin access, you can update your role in the database:

```python
import sqlite3
conn = sqlite3.connect('backend/data/studyflow.db')
conn.execute("UPDATE users SET role='admin' WHERE email='your@email.com'")
conn.commit()
conn.close()
```

Then visit `/admin` for the dashboard.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI, SQLAlchemy |
| AI | OpenAI API (GPT-4o-mini) |
| Vector DB | ChromaDB |
| Database | SQLite (async) |
| Auth | JWT + bcrypt |
| Frontend | Vanilla JS, CSS |
| Deployment | Docker, Nginx |

## Project Structure

```
ia/
├── backend/
│   ├── main.py              # FastAPI entry point
│   ├── config.py             # Environment configuration
│   ├── models/               # SQLAlchemy models
│   ├── routers/              # API endpoints
│   ├── services/             # Business logic
│   ├── data/                 # SQLite + ChromaDB (auto-created)
│   └── uploads/              # File storage (auto-created)
├── frontend/
│   ├── index.html            # Main chat page
│   ├── login.html            # Login page
│   ├── register.html         # Register page
│   ├── admin.html            # Admin dashboard
│   ├── css/                  # Stylesheets
│   └── js/                   # JavaScript modules
├── .env                      # Environment variables
├── Dockerfile                # Container build
├── docker-compose.yml        # Orchestration
└── nginx.conf                # Reverse proxy
```

## Docker Deployment

```bash
docker-compose up -d --build
```

The app will be available at `http://localhost:80`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login |
| GET | `/api/auth/me` | Current user |
| WS | `/api/chat/ws/{id}` | Streaming chat |
| POST | `/api/chat` | REST chat |
| GET | `/api/conversations` | List conversations |
| POST | `/api/files/upload` | Upload files |
| GET | `/api/admin/stats` | Admin stats |

## License

MIT

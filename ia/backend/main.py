"""
StudyFlow AI - Main Application Entry Point
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from backend.models.database import init_db
from backend.routers import auth, chat, conversations, files, admin

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    print("Database initialized")
    print("KHABACH AI is running!")
    yield
    print("Shutting down KHABACH AI")


app = FastAPI(
    title="KHABACH AI",
    description="Premium AI-powered educational platform",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routers
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(conversations.router)
app.include_router(files.router)
app.include_router(admin.router)

# Serve frontend static files
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIR / "assets")), name="assets")


@app.get("/")
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


@app.get("/login")
async def serve_login():
    return FileResponse(str(FRONTEND_DIR / "login.html"))


@app.get("/register")
async def serve_register():
    return FileResponse(str(FRONTEND_DIR / "register.html"))


@app.get("/admin")
async def serve_admin():
    return FileResponse(str(FRONTEND_DIR / "admin.html"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import engine, Base
from app.models import User, Question, Exam, ExamQuestion, ExamSession, Answer, ProctorEvent
from app.routers import auth, questions, exams, sessions, proctor, grading

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI-Based Intelligent Examination Platform",
    description="Automated Proctoring, Timed Exam Engine, AI Subjective Grading, & Candidate Performance Analysis",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(auth.router)
app.include_router(questions.router)
app.include_router(exams.router)
app.include_router(sessions.router)
app.include_router(proctor.router)
app.include_router(grading.router)


@app.get("/")
def read_root():
    index_path = Path(__file__).parent / "frontend" / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "AI Exam Platform API is running. Access /docs for Swagger UI."}

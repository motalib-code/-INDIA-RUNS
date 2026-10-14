from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Enum as SQLEnum,
)
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class UserRole(str, enum.Enum):
    STUDENT = "student"
    EXAMINER = "examiner"
    ADMIN = "admin"


class QuestionType(str, enum.Enum):
    MCQ = "mcq"
    MULTI_SELECT = "multi_select"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    IMAGE_UPLOAD = "image_upload"


class DifficultyLevel(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class SessionStatus(str, enum.Enum):
    ACTIVE = "active"
    SUBMITTED = "submitted"
    TIMEOUT = "timeout"


class AnswerStatus(str, enum.Enum):
    PENDING = "pending"
    GRADED = "graded"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.STUDENT, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    questions_created = relationship("Question", back_populates="creator")
    exams_created = relationship("Exam", back_populates="creator")
    exam_sessions = relationship("ExamSession", back_populates="student")


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String(100), index=True, nullable=False)
    difficulty = Column(SQLEnum(DifficultyLevel), default=DifficultyLevel.MEDIUM, nullable=False)
    question_type = Column(SQLEnum(QuestionType), nullable=False)
    question_text = Column(Text, nullable=False)
    options = Column(JSON, nullable=True)  # List of options for MCQ/multi-select
    correct_options = Column(JSON, nullable=True)  # List/value of correct option(s)
    model_answer = Column(Text, nullable=True)  # For subjective questions
    marks = Column(Float, default=1.0, nullable=False)
    negative_marks = Column(Float, default=0.0, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="questions_created")
    exam_questions = relationship("ExamQuestion", back_populates="question")


class Exam(Base):
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    subject = Column(String(100), index=True, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    passing_marks = Column(Float, default=40.0, nullable=False)
    total_marks = Column(Float, default=100.0, nullable=False)
    proctoring_enabled = Column(Boolean, default=True, nullable=False)
    gaze_threshold = Column(Float, default=0.7, nullable=False)
    tab_switch_limit = Column(Integer, default=3, nullable=False)
    randomization_mode = Column(Boolean, default=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", back_populates="exams_created")
    exam_questions = relationship("ExamQuestion", back_populates="exam", cascade="all, delete-orphan")
    exam_sessions = relationship("ExamSession", back_populates="exam", cascade="all, delete-orphan")


class ExamQuestion(Base):
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    order_index = Column(Integer, default=0, nullable=False)

    exam = relationship("Exam", back_populates="exam_questions")
    question = relationship("Question", back_populates="exam_questions")


class ExamSession(Base):
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True)
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_token = Column(String(255), unique=True, index=True, nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    status = Column(SQLEnum(SessionStatus), default=SessionStatus.ACTIVE, nullable=False)
    total_score = Column(Float, default=0.0, nullable=False)
    suspicion_score = Column(Float, default=0.0, nullable=False)
    tab_switch_count = Column(Integer, default=0, nullable=False)

    exam = relationship("Exam", back_populates="exam_sessions")
    student = relationship("User", back_populates="exam_sessions")
    answers = relationship("Answer", back_populates="session", cascade="all, delete-orphan")
    proctor_events = relationship("ProctorEvent", back_populates="session", cascade="all, delete-orphan")


class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False)
    submitted_answer = Column(JSON, nullable=True)  # Option index/indices or text string
    file_url = Column(String(500), nullable=True)  # For image/handwritten uploads
    ai_score = Column(Float, nullable=True)
    ai_justification = Column(Text, nullable=True)
    examiner_score = Column(Float, nullable=True)
    examiner_feedback = Column(Text, nullable=True)
    status = Column(SQLEnum(AnswerStatus), default=AnswerStatus.PENDING, nullable=False)

    session = relationship("ExamSession", back_populates="answers")
    question = relationship("Question")


class ProctorEvent(Base):
    __tablename__ = "proctor_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    event_type = Column(String(50), nullable=False)  # face_absent, multiple_faces, gaze_away, tab_switch, window_blur
    details = Column(Text, nullable=True)
    snapshot_url = Column(String(500), nullable=True)

    session = relationship("ExamSession", back_populates="proctor_events")

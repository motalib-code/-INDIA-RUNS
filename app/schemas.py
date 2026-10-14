from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models import UserRole, QuestionType, DifficultyLevel, SessionStatus, AnswerStatus


# Auth Schemas
class UserRegister(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    role: UserRole = UserRole.STUDENT


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: UserRole
    username: str
    user_id: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    user_id: Optional[int] = None


# Question Schemas
class QuestionCreate(BaseModel):
    subject: str
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    question_type: QuestionType
    question_text: str
    options: Optional[List[str]] = None
    correct_options: Optional[Any] = None  # List of ints for MCQ/multi-select, or string for short answer
    model_answer: Optional[str] = None
    marks: float = 1.0
    negative_marks: float = 0.0


class QuestionUpdate(BaseModel):
    subject: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    question_type: Optional[QuestionType] = None
    question_text: Optional[str] = None
    options: Optional[List[str]] = None
    correct_options: Optional[Any] = None
    model_answer: Optional[str] = None
    marks: Optional[float] = None
    negative_marks: Optional[float] = None


class QuestionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subject: str
    difficulty: DifficultyLevel
    question_type: QuestionType
    question_text: str
    options: Optional[List[str]] = None
    marks: float
    negative_marks: float
    creator_id: int


# Exam Schemas
class ExamCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject: str
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    passing_marks: float = 40.0
    total_marks: float = 100.0
    proctoring_enabled: bool = True
    gaze_threshold: float = 0.7
    tab_switch_limit: int = 3
    randomization_mode: bool = True
    question_ids: List[int] = Field(..., description="List of question IDs included in this exam")


class ExamUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    duration_minutes: Optional[int] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    passing_marks: Optional[float] = None
    total_marks: Optional[float] = None
    proctoring_enabled: Optional[bool] = None
    gaze_threshold: Optional[float] = None
    tab_switch_limit: Optional[int] = None
    randomization_mode: Optional[bool] = None
    question_ids: Optional[List[int]] = None


class ExamResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: Optional[str] = None
    subject: str
    duration_minutes: int
    start_time: datetime
    end_time: datetime
    passing_marks: float
    total_marks: float
    proctoring_enabled: bool
    gaze_threshold: float
    tab_switch_limit: int
    randomization_mode: bool
    creator_id: int
    questions: List[QuestionResponse] = []


# Exam Session & Answering Schemas
class ExamSessionStartResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    session_token: str
    exam_id: int
    duration_minutes: int
    start_time: datetime
    questions: List[QuestionResponse]


class AnswerSubmitRequest(BaseModel):
    question_id: int
    submitted_answer: Optional[Any] = None  # option index or text
    file_url: Optional[str] = None


class ExamSubmitRequest(BaseModel):
    answers: List[AnswerSubmitRequest]


# Proctoring Schemas
class ProctorEventCreate(BaseModel):
    event_type: str  # face_absent, multiple_faces, gaze_away, tab_switch, window_blur
    details: Optional[str] = None
    snapshot_url: Optional[str] = None


class ProctorHeartbeat(BaseModel):
    suspicion_increment: float = 5.0
    events: List[ProctorEventCreate] = []


# Grading Schemas
class GradingUpdate(BaseModel):
    examiner_score: float
    examiner_feedback: Optional[str] = None


class AnswerGradingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    question_id: int
    question_text: str
    question_type: QuestionType
    submitted_answer: Optional[Any] = None
    model_answer: Optional[str] = None
    ai_score: Optional[float] = None
    ai_justification: Optional[str] = None
    examiner_score: Optional[float] = None
    examiner_feedback: Optional[str] = None
    status: AnswerStatus


class StudentResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: int
    exam_id: int
    exam_title: str
    student_id: int
    student_name: str
    total_score: float
    max_marks: float
    status: SessionStatus
    passed: bool
    answers: List[AnswerGradingResponse] = []

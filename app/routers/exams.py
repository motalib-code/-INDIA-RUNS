from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Exam, ExamQuestion, Question, User, UserRole
from app.schemas import ExamCreate, ExamUpdate, ExamResponse, QuestionResponse
from app.services.auth import get_current_user, require_role

router = APIRouter(prefix="/api/exams", tags=["Exam Management"])


@router.post("/", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    # Verify all question IDs exist
    questions = db.query(Question).filter(Question.id.in_(exam_data.question_ids)).all()
    if len(questions) != len(set(exam_data.question_ids)):
        raise HTTPException(status_code=400, detail="One or more invalid question IDs provided")

    exam = Exam(
        title=exam_data.title,
        description=exam_data.description,
        subject=exam_data.subject,
        duration_minutes=exam_data.duration_minutes,
        start_time=exam_data.start_time,
        end_time=exam_data.end_time,
        passing_marks=exam_data.passing_marks,
        total_marks=exam_data.total_marks,
        proctoring_enabled=exam_data.proctoring_enabled,
        gaze_threshold=exam_data.gaze_threshold,
        tab_switch_limit=exam_data.tab_switch_limit,
        randomization_mode=exam_data.randomization_mode,
        creator_id=current_user.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # Link questions
    for idx, q_id in enumerate(exam_data.question_ids):
        eq = ExamQuestion(exam_id=exam.id, question_id=q_id, order_index=idx)
        db.add(eq)
    db.commit()

    # Construct response with questions
    response = ExamResponse.model_validate(exam)
    response.questions = [QuestionResponse.model_validate(q) for q in questions]
    return response


@router.get("/", response_model=List[ExamResponse])
def list_exams(
    subject: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Exam)
    if subject:
        query = query.filter(Exam.subject == subject)
    exams = query.all()

    result = []
    for exam in exams:
        resp = ExamResponse.model_validate(exam)
        eqs = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).all()
        q_ids = [eq.question_id for eq in eqs]
        questions = db.query(Question).filter(Question.id.in_(q_ids)).all()
        resp.questions = [QuestionResponse.model_validate(q) for q in questions]
        result.append(resp)
    return result


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    resp = ExamResponse.model_validate(exam)
    eqs = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).all()
    q_ids = [eq.question_id for eq in eqs]
    questions = db.query(Question).filter(Question.id.in_(q_ids)).all()
    resp.questions = [QuestionResponse.model_validate(q) for q in questions]
    return resp

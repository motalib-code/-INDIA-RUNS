from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Question, User, UserRole
from app.schemas import QuestionCreate, QuestionUpdate, QuestionResponse
from app.services.auth import get_current_user, require_role

router = APIRouter(prefix="/api/questions", tags=["Question Bank"])


@router.post("/", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    question = Question(
        subject=question_data.subject,
        difficulty=question_data.difficulty,
        question_type=question_data.question_type,
        question_text=question_data.question_text,
        options=question_data.options,
        correct_options=question_data.correct_options,
        model_answer=question_data.model_answer,
        marks=question_data.marks,
        negative_marks=question_data.negative_marks,
        creator_id=current_user.id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


@router.get("/", response_model=List[QuestionResponse])
def list_questions(
    subject: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Question)
    if subject:
        query = query.filter(Question.subject == subject)
    return query.all()


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    return question


@router.put("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: int,
    update_data: QuestionUpdate,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(question, field, value)

    db.commit()
    db.refresh(question)
    return question


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    db.delete(question)
    db.commit()
    return None

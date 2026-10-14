from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Answer, ExamSession, Question, User, UserRole, AnswerStatus
from app.schemas import GradingUpdate, AnswerGradingResponse
from app.services.auth import require_role
from app.services.evaluation import evaluate_session_answers

router = APIRouter(prefix="/api/grading", tags=["Examiner Grading Portal"])


@router.get("/pending", response_model=List[AnswerGradingResponse])
def get_pending_grading_answers(
    exam_id: int = None,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    query = db.query(Answer).filter(Answer.status == AnswerStatus.PENDING)
    if exam_id:
        query = query.join(ExamSession).filter(ExamSession.exam_id == exam_id)

    answers = query.all()
    results = []
    for ans in answers:
        q = db.query(Question).filter(Question.id == ans.question_id).first()
        results.append(
            AnswerGradingResponse(
                answer_id=ans.id,
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                submitted_answer=ans.submitted_answer,
                model_answer=q.model_answer,
                ai_score=ans.ai_score,
                ai_justification=ans.ai_justification,
                examiner_score=ans.examiner_score,
                examiner_feedback=ans.examiner_feedback,
                status=ans.status,
            )
        )
    return results


@router.put("/answer/{answer_id}", response_model=AnswerGradingResponse)
def grade_answer(
    answer_id: int,
    grading_data: GradingUpdate,
    current_user: User = Depends(require_role(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    ans = db.query(Answer).filter(Answer.id == answer_id).first()
    if not ans:
        raise HTTPException(status_code=404, detail="Answer not found")

    q = db.query(Question).filter(Question.id == ans.question_id).first()
    if grading_data.examiner_score > q.marks or grading_data.examiner_score < 0:
        raise HTTPException(status_code=400, detail=f"Score must be between 0 and {q.marks}")

    ans.examiner_score = grading_data.examiner_score
    ans.examiner_feedback = grading_data.examiner_feedback
    ans.status = AnswerStatus.GRADED
    db.commit()

    # Recalculate session total score
    session = db.query(ExamSession).filter(ExamSession.id == ans.session_id).first()
    if session:
        all_answers = db.query(Answer).filter(Answer.session_id == session.id).all()
        total = sum([a.examiner_score if a.examiner_score is not None else (a.ai_score or 0.0) for a in all_answers])
        session.total_score = total
        db.commit()

    db.refresh(ans)
    return AnswerGradingResponse(
        answer_id=ans.id,
        question_id=q.id,
        question_text=q.question_text,
        question_type=q.question_type,
        submitted_answer=ans.submitted_answer,
        model_answer=q.model_answer,
        ai_score=ans.ai_score,
        ai_justification=ans.ai_justification,
        examiner_score=ans.examiner_score,
        examiner_feedback=ans.examiner_feedback,
        status=ans.status,
    )

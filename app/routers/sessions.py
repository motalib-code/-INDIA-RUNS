from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Exam, ExamSession, ExamQuestion, Question, Answer, User, UserRole, SessionStatus
from app.schemas import ExamSessionStartResponse, ExamSubmitRequest, QuestionResponse, StudentResultResponse, AnswerGradingResponse
from app.services.auth import get_current_user, require_role
from app.services.exam_engine import generate_student_paper, check_exam_timeout
from app.services.evaluation import evaluate_session_answers

router = APIRouter(prefix="/api/sessions", tags=["Exam Sessions"])


@router.post("/start/{exam_id}", response_model=ExamSessionStartResponse)
def start_exam_session(
    exam_id: int,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    session = generate_student_paper(db, exam, current_user.id)
    if check_exam_timeout(session, exam):
        raise HTTPException(status_code=400, detail="Exam time has expired or session closed")

    # Get questions in session order
    eqs = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).all()
    q_ids = [eq.question_id for eq in eqs]
    if exam.randomization_mode:
        import random
        rng = random.Random(f"{exam.id}-{current_user.id}")
        rng.shuffle(q_ids)

    questions = db.query(Question).filter(Question.id.in_(q_ids)).all()
    # Sort questions by q_ids order
    q_map = {q.id: q for q in questions}
    ordered_questions = [q_map[qid] for qid in q_ids if qid in q_map]

    return ExamSessionStartResponse(
        session_id=session.id,
        session_token=session.session_token,
        exam_id=exam.id,
        duration_minutes=exam.duration_minutes,
        start_time=session.start_time,
        questions=[QuestionResponse.model_validate(q) for q in ordered_questions],
    )


@router.post("/submit/{session_id}")
def submit_exam_session(
    session_id: int,
    submit_data: ExamSubmitRequest,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id, ExamSession.student_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
    if check_exam_timeout(session, exam):
        raise HTTPException(status_code=400, detail="Exam time expired")

    # Record answers
    for ans_req in submit_data.answers:
        existing_ans = (
            db.query(Answer)
            .filter(Answer.session_id == session.id, Answer.question_id == ans_req.question_id)
            .first()
        )
        if existing_ans:
            existing_ans.submitted_answer = ans_req.submitted_answer
            existing_ans.file_url = ans_req.file_url
        else:
            new_ans = Answer(
                session_id=session.id,
                question_id=ans_req.question_id,
                submitted_answer=ans_req.submitted_answer,
                file_url=ans_req.file_url,
            )
            db.add(new_ans)

    session.status = SessionStatus.SUBMITTED
    session.end_time = __import__('datetime').datetime.utcnow()
    db.commit()

    # Trigger evaluation
    total_score = evaluate_session_answers(db, session, exam)

    return {
        "status": "submitted",
        "session_id": session.id,
        "total_score": total_score,
        "max_marks": exam.total_marks,
    }


@router.get("/result/{session_id}", response_model=StudentResultResponse)
def get_exam_result(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if current_user.role == UserRole.STUDENT and session.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
    student = db.query(User).filter(User.id == session.student_id).first()

    answers = db.query(Answer).filter(Answer.session_id == session.id).all()
    ans_responses = []
    for ans in answers:
        q = db.query(Question).filter(Question.id == ans.question_id).first()
        ans_responses.append(
            AnswerGradingResponse(
                answer_id=ans.id,
                question_id=q.id,
                question_text=q.question_text,
                question_type=q.question_type,
                submitted_answer=ans.submitted_answer,
                model_answer=q.model_answer if current_user.role != UserRole.STUDENT else None,
                ai_score=ans.ai_score,
                ai_justification=ans.ai_justification if current_user.role != UserRole.STUDENT else None,
                examiner_score=ans.examiner_score,
                examiner_feedback=ans.examiner_feedback,
                status=ans.status,
            )
        )

    passed = session.total_score >= exam.passing_marks

    return StudentResultResponse(
        session_id=session.id,
        exam_id=exam.id,
        exam_title=exam.title,
        student_id=student.id,
        student_name=student.username,
        total_score=session.total_score,
        max_marks=exam.total_marks,
        status=session.status,
        passed=passed,
        answers=ans_responses,
    )

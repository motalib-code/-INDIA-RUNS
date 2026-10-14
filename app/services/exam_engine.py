import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import uuid

from app.models import Exam, ExamSession, SessionStatus, Question, ExamQuestion


def generate_student_paper(db: Session, exam: Exam, student_id: int) -> ExamSession:
    # Check if session already exists for student & exam
    existing_session = (
        db.query(ExamSession)
        .filter(ExamSession.exam_id == exam.id, ExamSession.student_id == student_id)
        .first()
    )
    if existing_session:
        return existing_session

    # Generate session token binding exam and student
    session_token = f"sess_{exam.id}_{student_id}_{uuid.uuid4().hex[:10]}"

    # Get exam questions
    exam_questions = db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).all()
    question_ids = [eq.question_id for eq in exam_questions]

    if exam.randomization_mode:
        # Deterministic shuffle per student ID so refresh maintains same order
        rng = random.Random(f"{exam.id}-{student_id}")
        rng.shuffle(question_ids)

    new_session = ExamSession(
        exam_id=exam.id,
        student_id=student_id,
        session_token=session_token,
        start_time=datetime.utcnow(),
        status=SessionStatus.ACTIVE,
        total_score=0.0,
        suspicion_score=0.0,
        tab_switch_count=0,
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return new_session


def check_exam_timeout(session: ExamSession, exam: Exam) -> bool:
    if session.status != SessionStatus.ACTIVE:
        return True

    elapsed_minutes = (datetime.utcnow() - session.start_time).total_seconds() / 60.0
    if elapsed_minutes > exam.duration_minutes:
        session.status = SessionStatus.TIMEOUT
        session.end_time = datetime.utcnow()
        return True
    return False

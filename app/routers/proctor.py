from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ExamSession, Exam, User, UserRole
from app.schemas import ProctorHeartbeat
from app.services.auth import get_current_user, require_role
from app.services.proctoring import process_proctor_heartbeat

router = APIRouter(prefix="/api/proctor", tags=["AI Proctoring"])


@router.post("/heartbeat/{session_id}")
def proctor_heartbeat(
    session_id: int,
    heartbeat: ProctorHeartbeat,
    current_user: User = Depends(require_role(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    session = db.query(ExamSession).filter(ExamSession.id == session_id, ExamSession.student_id == current_user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Exam session not found")

    exam = db.query(Exam).filter(Exam.id == session.exam_id).first()
    if not exam:
        raise HTTPException(status_code=404, detail="Exam not found")

    result = process_proctor_heartbeat(db, session, exam, heartbeat.events, heartbeat.suspicion_increment)
    return result

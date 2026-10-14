from sqlalchemy.orm import Session
from datetime import datetime
from typing import Dict, Any

from app.models import ExamSession, ProctorEvent, Exam, SessionStatus


def process_proctor_heartbeat(
    db: Session,
    session: ExamSession,
    exam: Exam,
    events: list,
    suspicion_increment: float = 5.0
) -> Dict[str, Any]:
    if session.status != SessionStatus.ACTIVE:
        return {
            "session_id": session.id,
            "suspicion_score": session.suspicion_score,
            "message": "Session is not active."
        }

    added_events = 0
    for ev in events:
        event_obj = ProctorEvent(
            session_id=session.id,
            timestamp=datetime.utcnow(),
            event_type=ev.event_type,
            details=ev.details,
            snapshot_url=ev.snapshot_url,
        )
        db.add(event_obj)
        added_events += 1

        if ev.event_type == "tab_switch":
            session.tab_switch_count += 1

    session.suspicion_score = min(100.0, session.suspicion_score + (len(events) * suspicion_increment))
    db.commit()

    warning_flag = False
    action = "continue"

    if session.tab_switch_count >= exam.tab_switch_limit:
        warning_flag = True
        action = "warning_limit_exceeded"

    if session.suspicion_score >= 80.0:
        warning_flag = True
        action = "high_suspicion_flag"

    return {
        "session_id": session.id,
        "suspicion_score": session.suspicion_score,
        "tab_switch_count": session.tab_switch_count,
        "tab_switch_limit": exam.tab_switch_limit,
        "warning_flag": warning_flag,
        "action": action,
        "events_logged": added_events
    }

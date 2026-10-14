import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_exam_platform.db"

from app.database import Base, engine, SessionLocal, get_db
from app.main import app
from app.models import User, Question, Exam, ExamQuestion, ExamSession, Answer, ProctorEvent

# Re-create tables for test db
Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200


def test_auth_workflow():
    # 1. Register Examiner
    reg_res = client.post(
        "/api/auth/register",
        json={
            "username": "prof_alice",
            "email": "alice@university.edu",
            "password": "securepassword123",
            "role": "examiner",
        },
    )
    assert reg_res.status_code == 201
    data = reg_res.json()
    assert data["username"] == "prof_alice"
    assert data["role"] == "examiner"
    assert "access_token" in data

    # 2. Register Student
    stud_res = client.post(
        "/api/auth/register",
        json={
            "username": "student_bob",
            "email": "bob@student.edu",
            "password": "securepassword123",
            "role": "student",
        },
    )
    assert stud_res.status_code == 201
    stud_data = stud_res.json()
    assert stud_data["username"] == "student_bob"
    assert stud_data["role"] == "student"


def test_question_and_exam_workflow():
    # Login as examiner
    login_res = client.post(
        "/api/auth/login",
        data={"username": "prof_alice", "password": "securepassword123"},
    )
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create MCQ Question
    q_res = client.post(
        "/api/questions/",
        headers=headers,
        json={
            "subject": "Data Structures",
            "difficulty": "medium",
            "question_type": "mcq",
            "question_text": "What is the time complexity of binary search?",
            "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"],
            "correct_options": 1,
            "marks": 5.0,
            "negative_marks": 1.0,
        },
    )
    assert q_res.status_code == 201
    q_id = q_res.json()["id"]

    # Create Subjective Question
    sub_q_res = client.post(
        "/api/questions/",
        headers=headers,
        json={
            "subject": "Data Structures",
            "difficulty": "hard",
            "question_type": "short_answer",
            "question_text": "Explain hash collision resolution techniques.",
            "model_answer": "Chaining and open addressing are primary collision resolution methods in hash tables.",
            "marks": 10.0,
            "negative_marks": 0.0,
        },
    )
    assert sub_q_res.status_code == 201
    sub_q_id = sub_q_res.json()["id"]

    # Create Exam
    now = datetime.utcnow()
    exam_res = client.post(
        "/api/exams/",
        headers=headers,
        json={
            "title": "Algorithms Midterm Exam",
            "description": "Midterm evaluation for data structures and algorithms.",
            "subject": "Data Structures",
            "duration_minutes": 60,
            "start_time": now.isoformat(),
            "end_time": (now + timedelta(days=1)).isoformat(),
            "passing_marks": 10.0,
            "total_marks": 15.0,
            "question_ids": [q_id, sub_q_id],
        },
    )
    assert exam_res.status_code == 201
    exam_data = exam_res.json()
    assert exam_data["title"] == "Algorithms Midterm Exam"
    assert len(exam_data["questions"]) == 2
    exam_id = exam_data["id"]

    # Login as student
    stud_login = client.post(
        "/api/auth/login",
        data={"username": "student_bob", "password": "securepassword123"},
    )
    assert stud_login.status_code == 200
    stud_token = stud_login.json()["access_token"]
    stud_headers = {"Authorization": f"Bearer {stud_token}"}

    # Start Exam Session
    session_res = client.post(f"/api/sessions/start/{exam_id}", headers=stud_headers)
    assert session_res.status_code == 200
    session_data = session_res.json()
    session_id = session_data["session_id"]
    assert len(session_data["questions"]) == 2

    # Proctor heartbeat test (while session is active)
    proctor_res = client.post(
        f"/api/proctor/heartbeat/{session_id}",
        headers=stud_headers,
        json={
            "suspicion_increment": 2.0,
            "events": [{"event_type": "gaze_away", "details": "Looked away for 3 seconds"}]
        },
    )
    assert proctor_res.status_code == 200
    proctor_data = proctor_res.json()
    assert proctor_data["session_id"] == session_id
    assert proctor_data["suspicion_score"] > 0.0

    # Submit Answers
    submit_res = client.post(
        f"/api/sessions/submit/{session_id}",
        headers=stud_headers,
        json={
            "answers": [
                {"question_id": q_id, "submitted_answer": 1},  # Correct MCQ
                {"question_id": sub_q_id, "submitted_answer": "Chaining and open addressing resolve hash collisions."},  # Subjective answer
            ]
        },
    )
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["status"] == "submitted"
    assert sub_data["total_score"] > 0.0

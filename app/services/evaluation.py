from sqlalchemy.orm import Session
from typing import List, Dict, Any
import random

from app.models import ExamSession, Answer, Question, QuestionType, AnswerStatus, Exam


def evaluate_session_answers(db: Session, session: ExamSession, exam: Exam) -> float:
    answers = db.query(Answer).filter(Answer.session_id == session.id).all()
    total_score = 0.0

    for ans in answers:
        question = db.query(Question).filter(Question.id == ans.question_id).first()
        if not question:
            continue

        if question.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
            # Auto-evaluation
            score = evaluate_objective_answer(question, ans.submitted_answer)
            ans.ai_score = score
            ans.examiner_score = score
            ans.status = AnswerStatus.GRADED
            total_score += score
        elif question.question_type in [QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER, QuestionType.IMAGE_UPLOAD]:
            # LLM-based evaluation pipeline for subjective questions
            ai_score, justification = evaluate_subjective_answer(question, ans.submitted_answer)
            ans.ai_score = ai_score
            ans.ai_justification = justification
            ans.examiner_score = ai_score  # Pre-filled for examiner review
            ans.status = AnswerStatus.PENDING  # Queued for examiner review
            total_score += ai_score

    session.total_score = total_score
    db.commit()
    return total_score


def evaluate_objective_answer(question: Question, submitted_answer: Any) -> float:
    if submitted_answer is None:
        return 0.0

    correct = question.correct_options
    marks = question.marks
    negative_marks = question.negative_marks

    if question.question_type == QuestionType.MCQ:
        # submitted_answer could be int or index
        if submitted_answer == correct or str(submitted_answer) == str(correct):
            return marks
        else:
            return -negative_marks

    elif question.question_type == QuestionType.MULTI_SELECT:
        # submitted_answer expected to be list of selections
        if isinstance(submitted_answer, list) and isinstance(correct, list):
            sub_set = set(submitted_answer)
            corr_set = set(correct)
            if sub_set == corr_set:
                return marks
            elif sub_set.issubset(corr_set) and len(sub_set) > 0:
                return marks * 0.5  # Partial credit rule
            else:
                return -negative_marks
        elif submitted_answer == correct:
            return marks
        else:
            return -negative_marks

    return 0.0


def evaluate_subjective_answer(question: Question, submitted_answer: Any) -> (float, str):
    """
    Simulates LLM-based evaluation (GPT-4o style) comparing student answer against model answer.
    Returns (suggested_score, justification).
    """
    if not submitted_answer or not isinstance(submitted_answer, str) or len(submitted_answer.strip()) == 0:
        return 0.0, "No answer provided or answer is empty."

    model_ans = question.model_answer or ""
    max_marks = question.marks

    # Heuristic similarity & keyword matching simulation for robust grading
    words_submitted = set(submitted_answer.lower().split())
    words_model = set(model_ans.lower().split())

    if not words_model:
        return max_marks * 0.7, "Evaluated by AI: Answer provided but no rubric model answer specified."

    common_words = words_submitted.intersection(words_model)
    ratio = len(common_words) / max(len(words_model), 1)

    suggested_score = round(min(max(ratio * max_marks, max_marks * 0.2), max_marks), 2)

    # If substantial length and keyword overlap
    if len(words_submitted) > 10 and ratio > 0.3:
        suggested_score = round(max_marks * 0.85, 2)
        justification = f"AI Evaluation: Strong conceptual alignment. Matched key domain terms ({len(common_words)} keywords). Clear explanation."
    elif len(words_submitted) > 5:
        suggested_score = round(max_marks * 0.5, 2)
        justification = f"AI Evaluation: Moderate response. Partial keyword coverage ({len(common_words)} keywords). Needs further elaboration."
    else:
        suggested_score = round(max_marks * 0.2, 2)
        justification = "AI Evaluation: Response is too brief or lacks core concepts mentioned in model answer."

    return suggested_score, justification

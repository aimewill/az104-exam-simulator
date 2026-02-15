"""API routes for exam sessions."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Question, ExamSession, User
from ..services.session_service import SessionService
from ..auth import get_current_user, require_auth

router = APIRouter(prefix="/api/session", tags=["session"])


class StartSessionRequest(BaseModel):
    mode: str = "random"  # random, unseen, weak, review_wrong
    time_limit_minutes: Optional[int] = None


class AnswerRequest(BaseModel):
    question_id: int
    selected: List[str]
    flagged: bool = False


class SessionResponse(BaseModel):
    id: int
    mode: str
    total_questions: int
    time_limit_minutes: Optional[int]
    question_ids: List[int]
    current_answers: dict


@router.get("/study")
def get_study_questions(db: Session = Depends(get_db)):
    """Get all study-type questions (DRAG DROP, HOTSPOT) for review."""
    questions = db.query(Question).filter(
        Question.question_type == "study"
    ).order_by(Question.times_shown, Question.id).all()
    
    seen_count = sum(1 for q in questions if q.times_shown > 0)
    
    return {
        "questions": [
            {
                "id": q.id,
                "text": q.text,
                "explanation": q.explanation,
                "question_type": q.question_type,
                "domain_id": q.domain_id,
                "times_shown": q.times_shown,
            }
            for q in questions
        ],
        "total": len(questions),
        "seen": seen_count,
        "unseen": len(questions) - seen_count,
    }


@router.post("/study/{question_id}/seen")
def mark_study_question_seen(question_id: int, db: Session = Depends(get_db)):
    """Mark a study question as seen (increment times_shown)."""
    question = db.query(Question).filter(
        Question.id == question_id,
        Question.question_type == "study"
    ).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Study question not found")
    
    question.times_shown += 1
    db.commit()
    
    return {"success": True, "times_shown": question.times_shown}


@router.post("/start", response_model=SessionResponse)
def start_session(
    request: StartSessionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_auth),
):
    """Start a new exam session. Requires authentication."""
    service = SessionService(db)
    
    try:
        session = service.start_session(
            mode=request.mode,
            time_limit_minutes=request.time_limit_minutes,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return SessionResponse(
        id=session.id,
        mode=session.mode,
        total_questions=session.total_questions,
        time_limit_minutes=session.time_limit_minutes,
        question_ids=session.question_ids,
        current_answers=session.answers or {},
    )


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get session details."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session": session.to_dict(),
        "is_completed": session.completed_at is not None,
    }


@router.get("/{session_id}/questions")
def get_session_questions(session_id: int, db: Session = Depends(get_db)):
    """Get all questions for a session (only show answers after submission)."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Only include answers if session is completed (submitted)
    include_answers = session.completed_at is not None
    
    questions = []
    for qid in session.question_ids:
        question = db.query(Question).filter(Question.id == qid).first()
        if question:
            q_dict = question.to_dict(include_answer=include_answers)
            # Add user's answer if exists
            answer_data = (session.answers or {}).get(str(qid), {})
            q_dict["user_selected"] = answer_data.get("selected", [])
            q_dict["user_flagged"] = answer_data.get("flagged", False)
            questions.append(q_dict)
    
    return {
        "session_id": session_id,
        "questions": questions,
        "total": len(questions),
        "is_completed": session.completed_at is not None,
    }


@router.get("/{session_id}/question/{index}")
def get_question_by_index(session_id: int, index: int, db: Session = Depends(get_db)):
    """Get a specific question by its index in the session."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if index < 0 or index >= len(session.question_ids):
        raise HTTPException(status_code=404, detail="Question index out of range")
    
    qid = session.question_ids[index]
    question = db.query(Question).filter(Question.id == qid).first()
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    include_answers = session.completed_at is not None
    q_dict = question.to_dict(include_answer=include_answers)
    
    # Add user's answer
    answer_data = (session.answers or {}).get(str(qid), {})
    q_dict["user_selected"] = answer_data.get("selected", [])
    q_dict["user_flagged"] = answer_data.get("flagged", False)
    
    return {
        "index": index,
        "total": len(session.question_ids),
        "question": q_dict,
        "is_completed": session.completed_at is not None,
    }


@router.post("/answer")
def record_answer(request: AnswerRequest, session_id: int, db: Session = Depends(get_db)):
    """Record an answer for a question."""
    service = SessionService(db)
    
    try:
        session = service.record_answer(
            session_id=session_id,
            question_id=request.question_id,
            selected=request.selected,
            flagged=request.flagged,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return {
        "success": True,
        "answers_recorded": len(session.answers or {}),
    }


@router.post("/{session_id}/submit")
def submit_session(session_id: int, db: Session = Depends(get_db)):
    """Submit and grade the exam session."""
    service = SessionService(db)
    
    try:
        results = service.submit_session(session_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    return results


@router.get("/{session_id}/results")
def get_session_results(session_id: int, db: Session = Depends(get_db)):
    """Get detailed results for a completed session."""
    service = SessionService(db)
    results = service.get_session_results(session_id)
    
    if not results:
        raise HTTPException(status_code=404, detail="Results not found. Session may not be completed.")
    
    return results


@router.get("/{session_id}/navigator")
def get_navigator_status(session_id: int, db: Session = Depends(get_db)):
    """Get question status for the navigator UI."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    statuses = []
    for i, qid in enumerate(session.question_ids):
        answer_data = (session.answers or {}).get(str(qid), {})
        selected = answer_data.get("selected", [])
        flagged = answer_data.get("flagged", False)
        
        status = "unanswered"
        if selected:
            status = "answered"
        if flagged:
            status = "flagged" if not selected else "answered_flagged"
        
        statuses.append({
            "index": i,
            "question_id": qid,
            "status": status,
        })
    
    return {
        "session_id": session_id,
        "statuses": statuses,
        "total": len(statuses),
        "answered": sum(1 for s in statuses if "answered" in s["status"]),
        "flagged": sum(1 for s in statuses if "flagged" in s["status"]),
    }


@router.get("/{session_id}/time")
def get_time_status(session_id: int, db: Session = Depends(get_db)):
    """Get current timer status for a session."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
        "session_id": session_id,
        "time_limit_minutes": session.time_limit_minutes,
        "time_remaining_seconds": session.time_remaining_seconds,
        "is_paused": session.is_paused,
        "is_time_expired": session.is_time_expired,
        "is_completed": session.completed_at is not None,
    }


@router.post("/{session_id}/pause")
def pause_timer(session_id: int, db: Session = Depends(get_db)):
    """Pause the exam timer."""
    from datetime import datetime
    
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.completed_at:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    if not session.time_limit_minutes:
        raise HTTPException(status_code=400, detail="Session has no time limit")
    
    if session.paused_at:
        raise HTTPException(status_code=400, detail="Timer already paused")
    
    session.paused_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    
    return {
        "success": True,
        "is_paused": True,
        "time_remaining_seconds": session.time_remaining_seconds,
    }


@router.post("/{session_id}/resume")
def resume_timer(session_id: int, db: Session = Depends(get_db)):
    """Resume a paused exam timer."""
    from datetime import datetime
    
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    if session.completed_at:
        raise HTTPException(status_code=400, detail="Session already completed")
    
    if not session.paused_at:
        raise HTTPException(status_code=400, detail="Timer is not paused")
    
    # Add paused duration to total
    paused_duration = (datetime.utcnow() - session.paused_at).total_seconds()
    session.total_paused_seconds = (session.total_paused_seconds or 0) + int(paused_duration)
    session.paused_at = None
    
    db.commit()
    db.refresh(session)
    
    return {
        "success": True,
        "is_paused": False,
        "time_remaining_seconds": session.time_remaining_seconds,
    }

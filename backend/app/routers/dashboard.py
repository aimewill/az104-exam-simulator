"""API routes for dashboard and statistics."""
import csv
import io
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..database import get_db
from ..models import Question, ExamSession, DomainStats
from ..services.domain_classifier import get_classifier

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard")
def get_dashboard(db: Session = Depends(get_db)):
    """Get dashboard data including recent sessions, stats, and weak areas."""
    # Get last 10 completed sessions
    recent_sessions = db.query(ExamSession).filter(
        ExamSession.completed_at.isnot(None)
    ).order_by(desc(ExamSession.completed_at)).limit(10).all()
    
    # Get domain stats
    domain_stats = db.query(DomainStats).all()
    classifier = get_classifier()
    
    # Calculate weak domains (accuracy < 70%)
    weak_domains = [
        {
            **stat.to_dict(),
            "domain_name": classifier.get_domain_name(stat.domain_id),
        }
        for stat in domain_stats
        if stat.total_shown > 0 and stat.accuracy < 0.7
    ]
    weak_domains.sort(key=lambda x: x["accuracy"])
    
    # Calculate overall stats
    total_questions = db.query(Question).count()
    total_sessions = db.query(ExamSession).filter(
        ExamSession.completed_at.isnot(None)
    ).count()
    
    # Calculate average score
    completed_sessions = db.query(ExamSession).filter(
        ExamSession.completed_at.isnot(None)
    ).all()
    
    avg_score = 0
    if completed_sessions:
        avg_score = sum(s.scaled_score or 0 for s in completed_sessions) / len(completed_sessions)
    
    # Trend data for chart
    trend_data = [
        {
            "session_id": s.id,
            "date": s.completed_at.isoformat() if s.completed_at else None,
            "scaled_score": s.scaled_score,
            "passed": s.passed,
            "mode": s.mode,
        }
        for s in recent_sessions
    ]
    trend_data.reverse()  # Oldest to newest for chart
    
    return {
        "overview": {
            "total_questions": total_questions,
            "total_sessions": total_sessions,
            "average_score": round(avg_score),
            "passing_rate": round(
                sum(1 for s in completed_sessions if s.passed) / len(completed_sessions) * 100
                if completed_sessions else 0
            ),
        },
        "recent_sessions": [
            {
                "id": s.id,
                "date": s.completed_at.isoformat() if s.completed_at else None,
                "mode": s.mode,
                "correct": s.correct_count,
                "total": s.total_questions,
                "percent_score": round(s.percent_score or 0, 1),
                "scaled_score": s.scaled_score,
                "passed": s.passed,
            }
            for s in recent_sessions
        ],
        "weak_domains": weak_domains[:5],  # Top 5 weakest
        "domain_breakdown": [
            {
                **stat.to_dict(),
                "domain_name": classifier.get_domain_name(stat.domain_id),
            }
            for stat in domain_stats
        ],
        "trend_data": trend_data,
    }


@router.get("/domains")
def get_domains(db: Session = Depends(get_db)):
    """Get all domain definitions and stats."""
    classifier = get_classifier()
    domain_stats = {s.domain_id: s.to_dict() for s in db.query(DomainStats).all()}
    
    domains = []
    for domain in classifier.get_all_domains():
        stats = domain_stats.get(domain["id"], {})
        domains.append({
            "id": domain["id"],
            "name": domain["name"],
            "keywords_count": len(domain.get("keywords", [])),
            "total_questions": stats.get("total_questions", 0),
            "total_shown": stats.get("total_shown", 0),
            "total_correct": stats.get("total_correct", 0),
            "accuracy": stats.get("accuracy", 0),
        })
    
    return {"domains": domains}


@router.get("/export/missed.csv")
def export_missed_questions(db: Session = Depends(get_db)):
    """Export all missed questions to CSV."""
    # Get questions with incorrect answers
    questions = db.query(Question).filter(
        Question.times_shown > Question.times_correct,
        Question.times_shown > 0
    ).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow([
        "ID", "Question", "Correct Answer(s)", "Domain", 
        "Times Shown", "Times Correct", "Accuracy %", "Source Page"
    ])
    
    # Data rows
    for q in questions:
        writer.writerow([
            q.stable_id,
            q.text[:500],  # Truncate long questions
            ", ".join(q.correct_answers),
            q.domain_id,
            q.times_shown,
            q.times_correct,
            round(q.accuracy * 100, 1),
            q.source_page,
        ])
    
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=missed_questions.csv"}
    )


@router.get("/stats/questions")
def get_question_stats(db: Session = Depends(get_db)):
    """Get statistics about all questions."""
    total = db.query(Question).count()
    unseen = db.query(Question).filter(Question.times_shown == 0).count()
    
    # Group by domain
    classifier = get_classifier()
    domain_counts = {}
    
    questions = db.query(Question).all()
    for q in questions:
        domain = q.domain_id or "unknown"
        if domain not in domain_counts:
            domain_counts[domain] = 0
        domain_counts[domain] += 1
    
    return {
        "total": total,
        "unseen": unseen,
        "seen": total - unseen,
        "by_domain": [
            {
                "domain_id": did,
                "domain_name": classifier.get_domain_name(did),
                "count": count,
            }
            for did, count in domain_counts.items()
        ],
    }

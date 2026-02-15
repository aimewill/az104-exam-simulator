"""SQLAlchemy models for the exam simulator."""
import json
from datetime import datetime
from typing import List, Optional
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship

from .database import Base


class Question(Base):
    """A single exam question."""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    stable_id = Column(String(64), unique=True, index=True)  # Hash-based stable ID
    text = Column(Text, nullable=False)
    choices = Column(JSON, nullable=False)  # List of {"label": "A", "text": "..."}
    correct_answers = Column(JSON, nullable=False)  # List of correct labels ["A"] or ["A", "C"]
    explanation = Column(Text, nullable=True)
    question_type = Column(String(20), default="single")  # single, multi, truefalse, study
    domain_id = Column(String(50), nullable=True, index=True)
    source_file = Column(String(255), nullable=True)
    source_page = Column(Integer, nullable=True)
    exhibit_image = Column(String(255), nullable=True)  # Path to exhibit image
    series_id = Column(String(64), nullable=True, index=True)  # Groups related questions
    sequence_number = Column(Integer, nullable=True, index=True)  # Original PDF order
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Stats
    times_shown = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    
    @property
    def accuracy(self) -> float:
        if self.times_shown == 0:
            return 0.0
        return self.times_correct / self.times_shown
    
    def to_dict(self, include_answer: bool = False) -> dict:
        result = {
            "id": self.id,
            "stable_id": self.stable_id,
            "text": self.text,
            "choices": self.choices,
            "question_type": self.question_type,
            "domain_id": self.domain_id,
            "source_file": self.source_file,
            "source_page": self.source_page,
            "exhibit_image": self.exhibit_image,
            "series_id": self.series_id,
            "sequence_number": self.sequence_number,
        }
        if include_answer:
            result["correct_answers"] = self.correct_answers
            result["explanation"] = self.explanation
        return result


class ExamSession(Base):
    """An exam session (60 questions)."""
    __tablename__ = "exam_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    mode = Column(String(30), nullable=False)  # random, unseen, weak, review_wrong
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    time_limit_minutes = Column(Integer, nullable=True)
    
    # Timer pause tracking
    paused_at = Column(DateTime, nullable=True)  # When timer was paused
    total_paused_seconds = Column(Integer, default=0)  # Accumulated paused time
    
    # Results (filled after submission)
    total_questions = Column(Integer, default=60)
    correct_count = Column(Integer, nullable=True)
    percent_score = Column(Float, nullable=True)
    scaled_score = Column(Integer, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Question order and answers stored as JSON
    question_ids = Column(JSON, nullable=False)  # Ordered list of question IDs
    answers = Column(JSON, default=dict)  # {question_id: {"selected": ["A"], "flagged": false}}
    
    @property
    def time_remaining_seconds(self) -> Optional[int]:
        """Calculate remaining time in seconds."""
        if not self.time_limit_minutes or not self.started_at:
            return None
        if self.completed_at:
            return 0
        
        now = datetime.utcnow()
        elapsed = (now - self.started_at).total_seconds()
        
        # Subtract paused time
        elapsed -= (self.total_paused_seconds or 0)
        
        # If currently paused, don't count time since pause
        if self.paused_at:
            elapsed -= (now - self.paused_at).total_seconds()
        
        remaining = (self.time_limit_minutes * 60) - elapsed
        return max(0, int(remaining))
    
    @property
    def is_paused(self) -> bool:
        return self.paused_at is not None
    
    @property
    def is_time_expired(self) -> bool:
        remaining = self.time_remaining_seconds
        return remaining is not None and remaining <= 0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "mode": self.mode,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "time_limit_minutes": self.time_limit_minutes,
            "paused_at": self.paused_at.isoformat() if self.paused_at else None,
            "total_paused_seconds": self.total_paused_seconds or 0,
            "is_paused": self.is_paused,
            "time_remaining_seconds": self.time_remaining_seconds,
            "total_questions": self.total_questions,
            "correct_count": self.correct_count,
            "percent_score": self.percent_score,
            "scaled_score": self.scaled_score,
            "passed": self.passed,
            "question_ids": self.question_ids,
            "answers": self.answers,
        }


class ImportRecord(Base):
    """Record of PDF imports."""
    __tablename__ = "import_records"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    file_hash = Column(String(64), nullable=False)  # SHA256 of file
    imported_at = Column(DateTime, default=datetime.utcnow)
    questions_imported = Column(Integer, default=0)
    status = Column(String(20), default="pending")  # pending, completed, failed


class DomainStats(Base):
    """Aggregated stats per domain."""
    __tablename__ = "domain_stats"
    
    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(String(50), unique=True, index=True)
    domain_name = Column(String(100), nullable=False)
    total_questions = Column(Integer, default=0)
    total_shown = Column(Integer, default=0)
    total_correct = Column(Integer, default=0)
    
    @property
    def accuracy(self) -> float:
        if self.total_shown == 0:
            return 0.0
        return self.total_correct / self.total_shown
    
    def to_dict(self) -> dict:
        return {
            "domain_id": self.domain_id,
            "domain_name": self.domain_name,
            "total_questions": self.total_questions,
            "total_shown": self.total_shown,
            "total_correct": self.total_correct,
            "accuracy": self.accuracy,
        }

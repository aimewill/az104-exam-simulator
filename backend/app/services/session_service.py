"""Exam session service for managing exam logic."""
import random
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models import Question, ExamSession, DomainStats
from ..config import EXAM_QUESTION_COUNT, PASSING_SCORE, MAX_SCALED_SCORE


class SessionService:
    """Service for managing exam sessions."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_session(
        self,
        mode: str,
        time_limit_minutes: Optional[int] = None
    ) -> ExamSession:
        """Start a new exam session with selected questions."""
        # Get questions based on mode
        question_ids = self._select_questions(mode, EXAM_QUESTION_COUNT)
        
        if not question_ids:
            raise ValueError("No questions available for this mode")
        
        # Create session
        session = ExamSession(
            mode=mode,
            time_limit_minutes=time_limit_minutes,
            total_questions=len(question_ids),
            question_ids=question_ids,
            answers={},
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def _group_and_select_with_series(self, questions: List[Question], count: int) -> List[int]:
        """Group questions by series and select while keeping series together.
        
        Args:
            questions: List of Question objects to select from
            count: Target number of questions to select
            
        Returns:
            List of question IDs with series kept together
        """
        # Group questions by series_id
        series_groups = {}  # {series_id: [questions]}
        standalone_questions = []  # Questions not in a series
        
        for q in questions:
            if q.series_id:
                if q.series_id not in series_groups:
                    series_groups[q.series_id] = []
                series_groups[q.series_id].append(q)
            else:
                standalone_questions.append(q)
        
        # Convert series groups to tuples (all questions in series kept together)
        series_units = list(series_groups.values())
        
        # Randomize standalone questions
        random.shuffle(standalone_questions)
        
        # Randomize order of series units
        random.shuffle(series_units)
        
        # Build final selection
        selected_ids = []
        remaining_count = count
        
        # Add series units (all or nothing - keep series together)
        for series_questions in series_units:
            if len(selected_ids) >= count:
                break
            # Only add if the entire series fits
            if len(series_questions) <= remaining_count:
                # Sort by sequence number to maintain order within series
                series_questions.sort(key=lambda q: q.sequence_number)
                selected_ids.extend([q.id for q in series_questions])
                remaining_count -= len(series_questions)
        
        # Fill remaining slots with standalone questions
        for q in standalone_questions:
            if len(selected_ids) >= count:
                break
            selected_ids.append(q.id)
        
        return selected_ids[:count]
    
    def _select_questions(self, mode: str, count: int) -> List[int]:
        """Select questions based on the exam mode."""
        if mode == "random":
            return self._select_random(count)
        elif mode == "unseen":
            return self._select_unseen_first(count)
        elif mode == "weak":
            return self._select_weak_areas(count)
        elif mode == "review_wrong":
            return self._select_wrong_only(count)
        else:
            return self._select_random(count)
    
    def _select_random(self, count: int) -> List[int]:
        """Select random questions (excluding study-type and invalid questions).
        
        Questions in the same series are kept together in sequence.
        """
        questions = self.db.query(Question).filter(
            Question.question_type != 'study'
        ).order_by(Question.sequence_number).all()
        
        # Only include questions with at least 2 choices
        questions = [q for q in questions if len(q.choices or []) >= 2]
        
        # Group questions by series
        return self._group_and_select_with_series(questions, count)
    
    def _select_unseen_first(self, count: int) -> List[int]:
        """Prioritize questions that haven't been shown (excluding study-type).
        
        Series questions are kept together.
        """
        # Get all valid questions
        all_questions = self.db.query(Question).filter(
            Question.question_type != 'study'
        ).order_by(Question.times_shown, Question.sequence_number).all()
        
        # Filter to valid questions (at least 2 choices)
        valid_questions = [q for q in all_questions if len(q.choices or []) >= 2]
        
        # Sort so unseen (times_shown=0) come first
        valid_questions.sort(key=lambda q: (q.times_shown, q.sequence_number))
        
        # Use series grouping
        return self._group_and_select_with_series(valid_questions, count)
    
    def _select_weak_areas(self, count: int) -> List[int]:
        """Oversample questions from domains with low accuracy.
        
        Series questions are kept together.
        """
        # Get domain stats
        domain_stats = self.db.query(DomainStats).filter(
            DomainStats.total_shown > 0
        ).all()
        
        # Calculate weights (lower accuracy = higher weight)
        domain_weights = {}
        for stat in domain_stats:
            # Invert accuracy for weight, minimum 0.1
            weight = max(0.1, 1.0 - stat.accuracy)
            domain_weights[stat.domain_id] = weight
        
        if not domain_weights:
            return self._select_random(count)
        
        # Get all valid questions and assign weights
        all_questions = self.db.query(Question).filter(
            Question.question_type != 'study'
        ).order_by(Question.sequence_number).all()
        
        valid_questions = []
        for q in all_questions:
            if len(q.choices or []) < 2:
                continue
            weight = domain_weights.get(q.domain_id, 0.5)
            if q.times_shown > 0:
                q_weight = max(0.1, 1.0 - q.accuracy)
                weight = (weight + q_weight) / 2
            q._weight = weight  # Attach weight to question object
            valid_questions.append(q)
        
        # Sort by weight (higher weight = weaker = first)
        valid_questions.sort(key=lambda q: -getattr(q, '_weight', 0.5))
        
        # Use series grouping
        return self._group_and_select_with_series(valid_questions, count)
    
    def _select_wrong_only(self, count: int) -> List[int]:
        """Select only previously missed questions (excluding study-type).
        
        Series questions are kept together.
        """
        # Get questions that have been answered incorrectly (with at least 2 choices)
        wrong = self.db.query(Question).filter(
            Question.times_shown > Question.times_correct,
            Question.times_shown > 0,
            Question.question_type != 'study'
        ).order_by(Question.sequence_number).all()
        wrong = [q for q in wrong if len(q.choices or []) >= 2]
        
        if not wrong:
            # Fallback to random if no wrong answers
            return self._select_random(count)
        
        # Use series grouping
        return self._group_and_select_with_series(wrong, count)
    
    def record_answer(
        self,
        session_id: int,
        question_id: int,
        selected: List[str],
        flagged: bool = False
    ) -> ExamSession:
        """Record an answer for a question in a session."""
        session = self.db.query(ExamSession).filter(
            ExamSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.completed_at:
            raise ValueError("Session already completed")
        
        # Update answers
        answers = dict(session.answers) if session.answers else {}
        answers[str(question_id)] = {
            "selected": selected,
            "flagged": flagged,
        }
        session.answers = answers
        
        self.db.commit()
        self.db.refresh(session)
        
        return session
    
    def submit_session(self, session_id: int) -> Dict:
        """Submit and grade an exam session."""
        session = self.db.query(ExamSession).filter(
            ExamSession.id == session_id
        ).first()
        
        if not session:
            raise ValueError(f"Session {session_id} not found")
        
        if session.completed_at:
            raise ValueError("Session already submitted")
        
        # Grade each question
        correct_count = 0
        results = []
        
        for qid in session.question_ids:
            question = self.db.query(Question).filter(Question.id == qid).first()
            if not question:
                continue
            
            # Get user's answer
            answer_data = (session.answers or {}).get(str(qid), {})
            selected = answer_data.get("selected", [])
            
            # Check if correct
            is_correct = set(selected) == set(question.correct_answers)
            if is_correct:
                correct_count += 1
            
            # Update question stats
            question.times_shown += 1
            if is_correct:
                question.times_correct += 1
            
            # Update domain stats
            self._update_domain_stats(question.domain_id, is_correct)
            
            results.append({
                "question_id": qid,
                "selected": selected,
                "correct_answers": question.correct_answers,
                "is_correct": is_correct,
                "explanation": question.explanation,
                "domain_id": question.domain_id,
            })
        
        # Calculate scores
        total = session.total_questions
        percent_score = (correct_count / total * 100) if total > 0 else 0
        scaled_score = round(MAX_SCALED_SCORE * correct_count / total) if total > 0 else 0
        passed = scaled_score >= PASSING_SCORE
        
        # Update session
        session.completed_at = datetime.utcnow()
        session.correct_count = correct_count
        session.percent_score = percent_score
        session.scaled_score = scaled_score
        session.passed = passed
        
        self.db.commit()
        
        return {
            "session_id": session_id,
            "correct_count": correct_count,
            "total_questions": total,
            "percent_score": round(percent_score, 1),
            "scaled_score": scaled_score,
            "passed": passed,
            "passing_score": PASSING_SCORE,
            "results": results,
        }
    
    def _update_domain_stats(self, domain_id: str, is_correct: bool):
        """Update aggregated domain statistics."""
        if not domain_id:
            return
        
        stats = self.db.query(DomainStats).filter(
            DomainStats.domain_id == domain_id
        ).first()
        
        if stats:
            stats.total_shown += 1
            if is_correct:
                stats.total_correct += 1
    
    def get_session_results(self, session_id: int) -> Optional[Dict]:
        """Get detailed results for a completed session."""
        session = self.db.query(ExamSession).filter(
            ExamSession.id == session_id
        ).first()
        
        if not session or not session.completed_at:
            return None
        
        # Build detailed results
        question_results = []
        domain_breakdown = {}
        
        for qid in session.question_ids:
            question = self.db.query(Question).filter(Question.id == qid).first()
            if not question:
                continue
            
            answer_data = (session.answers or {}).get(str(qid), {})
            selected = answer_data.get("selected", [])
            is_correct = set(selected) == set(question.correct_answers)
            
            question_results.append({
                "question": question.to_dict(include_answer=True),
                "selected": selected,
                "is_correct": is_correct,
                "flagged": answer_data.get("flagged", False),
            })
            
            # Track domain stats
            domain = question.domain_id or "unknown"
            if domain not in domain_breakdown:
                domain_breakdown[domain] = {"total": 0, "correct": 0}
            domain_breakdown[domain]["total"] += 1
            if is_correct:
                domain_breakdown[domain]["correct"] += 1
        
        # Calculate domain accuracy
        for domain, stats in domain_breakdown.items():
            stats["accuracy"] = round(stats["correct"] / stats["total"] * 100, 1) if stats["total"] > 0 else 0
        
        return {
            "session": session.to_dict(),
            "questions": question_results,
            "domain_breakdown": domain_breakdown,
        }

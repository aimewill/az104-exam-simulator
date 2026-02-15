"""API routes for PDF import functionality."""
import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..database import get_db
from ..config import PDFS_DIR
from ..models import Question, ImportRecord, DomainStats
from ..services.parser import PDFParser, ParseReport, ParsedQuestion, get_demo_questions
from ..services.domain_classifier import get_classifier

router = APIRouter(prefix="/api/import", tags=["import"])

# Store scan results in memory for review before import
_scan_results: dict = {}


class ScanResponse(BaseModel):
    files_found: int
    reports: List[dict]
    needs_import: bool
    total_questions: int
    valid_questions: int
    issues_summary: dict


class QuestionEdit(BaseModel):
    stable_id: str
    text: Optional[str] = None
    choices: Optional[List[dict]] = None
    correct_answers: Optional[List[str]] = None
    domain_id: Optional[str] = None
    skip: bool = False


class ImportRequest(BaseModel):
    edits: Optional[List[QuestionEdit]] = None


@router.post("/scan", response_model=ScanResponse)
def scan_pdfs(db: Session = Depends(get_db)):
    """Scan PDF directory and parse all files."""
    global _scan_results
    
    # Find all PDFs
    pdf_files = list(PDFS_DIR.glob("*.pdf"))
    
    if not pdf_files:
        # No PDFs found - check if we should use demo data
        question_count = db.query(Question).count()
        if question_count == 0:
            # Load demo questions
            _scan_results = {
                "demo": True,
                "questions": get_demo_questions()
            }
            return ScanResponse(
                files_found=0,
                reports=[{"filename": "demo_questions", "total_questions": 5, "valid_questions": 5}],
                needs_import=True,
                total_questions=5,
                valid_questions=5,
                issues_summary={"info": "No PDFs found. Demo questions available for testing."}
            )
        return ScanResponse(
            files_found=0,
            reports=[],
            needs_import=False,
            total_questions=0,
            valid_questions=0,
            issues_summary={}
        )
    
    parser = PDFParser()
    reports = []
    all_questions = []
    issues_summary = {
        "missing_answers": 0,
        "broken_choices": 0,
        "duplicates": 0,
    }
    
    # Check which files need importing
    for pdf_path in pdf_files:
        file_hash = parser.get_file_hash(pdf_path)
        
        # Check if already imported
        existing = db.query(ImportRecord).filter(
            ImportRecord.filename == pdf_path.name,
            ImportRecord.file_hash == file_hash,
            ImportRecord.status == "completed"
        ).first()
        
        if existing:
            continue  # Skip already imported files
        
        # Parse the PDF
        report = parser.parse_pdf(pdf_path)
        reports.append({
            **report.to_dict(),
            "file_hash": file_hash,
            "questions": [
                {
                    "stable_id": q.stable_id,
                    "text": q.text[:200] + "..." if len(q.text) > 200 else q.text,
                    "choices_count": len(q.choices),
                    "has_answer": bool(q.correct_answers),
                    "domain_id": q.domain_id,
                    "issues": q.issues,
                    "source_page": q.source_page,
                }
                for q in report.questions
            ]
        })
        
        all_questions.extend(report.questions)
        issues_summary["missing_answers"] += report.missing_answers
        issues_summary["broken_choices"] += report.broken_choices
        issues_summary["duplicates"] += report.duplicates
    
    # Store for later import
    _scan_results = {
        "demo": False,
        "reports": reports,
        "questions": all_questions,
    }
    
    total_questions = sum(r.get("total_questions", 0) for r in reports)
    valid_questions = sum(r.get("valid_questions", 0) for r in reports)
    
    return ScanResponse(
        files_found=len(pdf_files),
        reports=reports,
        needs_import=len(reports) > 0,
        total_questions=total_questions,
        valid_questions=valid_questions,
        issues_summary=issues_summary,
    )


@router.post("/run")
def run_import(request: ImportRequest, db: Session = Depends(get_db)):
    """Import scanned questions into the database."""
    global _scan_results
    
    if not _scan_results:
        raise HTTPException(status_code=400, detail="No scan results. Run /scan first.")
    
    # Build edit lookup
    edits = {e.stable_id: e for e in (request.edits or [])}
    
    # Get questions to import
    if _scan_results.get("demo"):
        questions = _scan_results["questions"]
    else:
        questions = _scan_results.get("questions", [])
    
    imported = 0
    skipped = 0
    classifier = get_classifier()
    domain_counts = {}  # Track domain counts in memory to avoid duplicate inserts
    seen_stable_ids = set()  # Track seen stable_ids to skip duplicates in batch
    
    for q in questions:
        # Check for edits
        edit = edits.get(q.stable_id)
        
        if edit and edit.skip:
            skipped += 1
            continue
        
        # Apply edits if any
        if edit:
            if edit.text:
                q.text = edit.text
            if edit.choices:
                q.choices = edit.choices
            if edit.correct_answers:
                q.correct_answers = edit.correct_answers
            if edit.domain_id:
                q.domain_id = edit.domain_id
        
        # Skip invalid questions
        if not q.is_valid:
            skipped += 1
            continue
        
        # Check for existing question or duplicate in batch
        if q.stable_id in seen_stable_ids:
            skipped += 1
            continue
        
        existing = db.query(Question).filter(
            Question.stable_id == q.stable_id
        ).first()
        
        if existing:
            skipped += 1
            continue
        
        seen_stable_ids.add(q.stable_id)
        
        # Create question
        question = Question(
            stable_id=q.stable_id,
            text=q.text,
            choices=q.choices,
            correct_answers=q.correct_answers,
            explanation=q.explanation,
            question_type=q.question_type,
            domain_id=q.domain_id,
            source_file=getattr(q, 'source_file', None),
            source_page=q.source_page,
            exhibit_image=q.exhibit_image,
            series_id=q.series_id,
            sequence_number=q.sequence_number,
        )
        db.add(question)
        imported += 1
        
        # Track domain counts in memory
        if q.domain_id:
            domain_counts[q.domain_id] = domain_counts.get(q.domain_id, 0) + 1
    
    # Update domain stats after all questions processed
    for domain_id, count in domain_counts.items():
        stats = db.query(DomainStats).filter(
            DomainStats.domain_id == domain_id
        ).first()
        
        if stats:
            stats.total_questions += count
        else:
            stats = DomainStats(
                domain_id=domain_id,
                domain_name=classifier.get_domain_name(domain_id),
                total_questions=count,
            )
            db.add(stats)
    
    # Record imports
    if not _scan_results.get("demo"):
        for report in _scan_results.get("reports", []):
            record = ImportRecord(
                filename=report["filename"],
                file_hash=report.get("file_hash", ""),
                questions_imported=report.get("valid_questions", 0),
                status="completed"
            )
            db.add(record)
    
    db.commit()
    
    # Clear scan results
    _scan_results = {}
    
    return {
        "imported": imported,
        "skipped": skipped,
        "total_in_db": db.query(Question).count(),
    }


def _update_domain_question_count(db: Session, domain_id: str, classifier):
    """Update or create domain stats."""
    if not domain_id:
        return
    
    stats = db.query(DomainStats).filter(
        DomainStats.domain_id == domain_id
    ).first()
    
    if stats:
        stats.total_questions += 1
    else:
        stats = DomainStats(
            domain_id=domain_id,
            domain_name=classifier.get_domain_name(domain_id),
            total_questions=1,
        )
        db.add(stats)


@router.get("/report")
def get_import_report(db: Session = Depends(get_db)):
    """Get the current import report/scan results."""
    global _scan_results
    
    if not _scan_results:
        return {
            "has_scan": False,
            "questions_in_db": db.query(Question).count(),
        }
    
    if _scan_results.get("demo"):
        return {
            "has_scan": True,
            "is_demo": True,
            "questions": [
                {
                    "stable_id": q.stable_id,
                    "text": q.text,
                    "choices": q.choices,
                    "correct_answers": q.correct_answers,
                    "domain_id": q.domain_id,
                    "issues": q.issues,
                }
                for q in _scan_results["questions"]
            ],
        }
    
    return {
        "has_scan": True,
        "is_demo": False,
        "reports": _scan_results.get("reports", []),
        "questions_count": len(_scan_results.get("questions", [])),
    }


@router.get("/status")
def get_import_status(db: Session = Depends(get_db)):
    """Check if import is needed."""
    question_count = db.query(Question).count()
    pdf_files = list(PDFS_DIR.glob("*.pdf"))
    
    # Check for new/changed PDFs
    parser = PDFParser()
    new_files = []
    
    for pdf_path in pdf_files:
        file_hash = parser.get_file_hash(pdf_path)
        existing = db.query(ImportRecord).filter(
            ImportRecord.filename == pdf_path.name,
            ImportRecord.file_hash == file_hash,
            ImportRecord.status == "completed"
        ).first()
        
        if not existing:
            new_files.append(pdf_path.name)
    
    return {
        "questions_in_db": question_count,
        "pdf_files_found": len(pdf_files),
        "new_files": new_files,
        "needs_import": question_count == 0 or len(new_files) > 0,
    }

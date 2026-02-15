#!/usr/bin/env python3
"""Re-extract exhibit images and update database without losing question data."""

import sys
import os
import re
import hashlib
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.app.config import PDFS_DIR, EXHIBITS_DIR, DATABASE_URL
from backend.app.database import SessionLocal
from backend.app.models import Question

import fitz  # PyMuPDF


def normalize_text(text: str) -> str:
    """Normalize whitespace for matching."""
    return re.sub(r'\s+', ' ', text.lower()).strip()


def find_pdf_page_for_question(question_text: str, doc) -> int:
    """Find the actual PDF page containing this question text."""
    # Use first 150-200 chars for matching
    search_text = normalize_text(question_text[:180])
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = normalize_text(page.get_text("text"))
        if search_text in page_text:
            return page_num + 1  # 1-indexed
    
    # Try shorter match
    search_text = normalize_text(question_text[:100])
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = normalize_text(page.get_text("text"))
        if search_text in page_text:
            return page_num + 1
    
    return 0


def extract_image_for_question(doc, pdf_page_num: int, question: Question) -> str:
    """Extract the best image from surrounding pages using a scoring heuristic."""
    if pdf_page_num < 1:
        return None

    # Candidate pages: found page (0-indexed), previous, next
    pages_to_try = [pdf_page_num - 1]
    if pdf_page_num > 1:
        pages_to_try.append(pdf_page_num - 2)
    if pdf_page_num < len(doc):
        pages_to_try.append(pdf_page_num)  # next page

    q_text_lower = question.text.lower()
    expects_table = any(kw in q_text_lower for kw in [
        "following users", "following resources", "following table",
        "following virtual machines", "following storage accounts",
        "following subscriptions", "contains the following",
        "shown in the following", "contains the resources shown"
    ])

    best = None  # (score, bytes, ext, width, height, page_idx, img_index)

    for page_idx in sorted(set(pages_to_try)):
        if page_idx < 0 or page_idx >= len(doc):
            continue
        page = doc[page_idx]
        image_list = page.get_images(full=True)
        for img_index, img in enumerate(image_list):
            xref = img[0]
            try:
                base_image = doc.extract_image(xref)
                image_bytes = base_image["image"]
                image_ext = base_image["ext"]
                width = base_image.get("width", 0)
                height = base_image.get("height", 0)
                size = len(image_bytes)

                # Skip tiny icons
                if size < 5000:
                    continue

                # Table-like images (wide and short)
                is_table_like = width > 300 and height > 50 and width / max(height, 1) > 1.5

                # Scoring: prefer table-like if expected, otherwise largest
                score = size / 10000.0
                if expects_table and is_table_like:
                    score += 5.0
                elif is_table_like:
                    score += 1.0
                if page_idx == pdf_page_num - 1:
                    score += 0.5

                if not best or score > best[0]:
                    best = (score, image_bytes, image_ext, width, height, page_idx, img_index)
            except Exception as e:
                print(f"  Error extracting image: {e}")
                continue

    if not best:
        return None

    _, image_bytes, image_ext, width, height, page_idx, img_index = best
    stable_suffix = question.stable_id[:8] if question.stable_id else str(question.id)
    filename = f"q{question.source_page}_{stable_suffix}_img{page_idx}_{img_index}.{image_ext}"
    filepath = EXHIBITS_DIR / filename

    with open(filepath, "wb") as f:
        f.write(image_bytes)

    return f"/static/exhibits/{filename}"


def main():
    print("Re-extracting exhibit images...")
    print(f"PDF directory: {PDFS_DIR}")
    print(f"Exhibits directory: {EXHIBITS_DIR}")
    
    # Find PDF
    pdf_files = list(PDFS_DIR.glob("*.pdf"))
    if not pdf_files:
        print("ERROR: No PDF files found!")
        return
    
    pdf_path = pdf_files[0]
    print(f"Using PDF: {pdf_path.name}")
    
    # Open PDF
    doc = fitz.open(pdf_path)
    print(f"PDF has {len(doc)} pages")
    
    # Keywords that indicate exhibit/table needed
    exhibit_keywords = [
        "following exhibit", "shown in the following", "as shown in",
        "following diagram", "following image", "exhibit", "shown below"
    ]
    table_keywords = [
        "following users", "following resources", "following table",
        "following virtual machines", "following storage accounts",
        "following subscriptions", "contains the following",
        "following information", "following configuration",
        "following azure", "following settings"
    ]
    
    # Get questions from database
    db = SessionLocal()
    questions = db.query(Question).all()
    print(f"Found {len(questions)} questions in database")
    
    updated = 0
    errors = 0
    
    for q in questions:
        q_text_lower = q.text.lower()
        has_exhibit = any(kw in q_text_lower for kw in exhibit_keywords)
        has_table = any(kw in q_text_lower for kw in table_keywords)
        
        if not has_exhibit and not has_table:
            continue
        
        print(f"\nProcessing Q{q.source_page} (id={q.id})...")
        
        # Find the actual PDF page
        pdf_page = find_pdf_page_for_question(q.text, doc)
        if pdf_page == 0:
            print(f"  WARNING: Could not find PDF page for Q{q.source_page}")
            errors += 1
            continue
        
        print(f"  Found on PDF page {pdf_page}")
        
        # Extract image
        new_image_path = extract_image_for_question(doc, pdf_page, q)
        
        if new_image_path:
            old_path = q.exhibit_image
            q.exhibit_image = new_image_path
            print(f"  Image: {old_path} -> {new_image_path}")
            updated += 1
        else:
            print(f"  No suitable image found")
    
    # Commit changes
    db.commit()
    db.close()
    doc.close()
    
    print(f"\n=== Summary ===")
    print(f"Updated: {updated} questions")
    print(f"Errors: {errors} questions")
    print("Done!")


if __name__ == "__main__":
    main()

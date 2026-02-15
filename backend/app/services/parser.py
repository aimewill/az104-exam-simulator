"""PDF parser for extracting AZ-104 exam questions."""
import hashlib
import logging
import re
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from PIL import Image

from .domain_classifier import get_classifier
from ..config import EXHIBITS_DIR

logger = logging.getLogger(__name__)


@dataclass
class ParsedQuestion:
    """A question extracted from PDF."""
    text: str
    choices: List[Dict[str, str]]  # [{"label": "A", "text": "..."}]
    correct_answers: List[str]  # ["A"] or ["A", "C"]
    explanation: Optional[str] = None
    question_type: str = "single"  # single, multi, truefalse, study
    domain_id: Optional[str] = None
    source_page: int = 0
    exhibit_image: Optional[str] = None  # Path to exhibit image
    series_id: Optional[str] = None  # Groups related questions
    sequence_number: int = 0  # Original PDF order
    issues: List[str] = field(default_factory=list)
    
    @property
    def stable_id(self) -> str:
        """Generate a stable ID based on question content."""
        content = f"{self.text}|{'|'.join(c['text'] for c in self.choices)}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def is_valid(self) -> bool:
        """Check if question has minimum required fields."""
        # Study questions only need text and explanation
        if self.question_type == "study":
            return bool(self.text and self.explanation)
        return bool(self.text and self.choices and self.correct_answers)


@dataclass
class ParseReport:
    """Report of PDF parsing results."""
    filename: str
    total_questions: int = 0
    valid_questions: int = 0
    missing_answers: int = 0
    broken_choices: int = 0
    duplicates: int = 0
    page_issues: Dict[int, List[str]] = field(default_factory=dict)
    questions: List[ParsedQuestion] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "filename": self.filename,
            "total_questions": self.total_questions,
            "valid_questions": self.valid_questions,
            "missing_answers": self.missing_answers,
            "broken_choices": self.broken_choices,
            "duplicates": self.duplicates,
            "page_issues": self.page_issues,
        }


class PDFParser:
    """Parser for extracting questions from AZ-104 exam PDFs."""
    
    # Patterns for question parsing
    QUESTION_START = re.compile(
        r'^(?:QUESTION\s*(?:NO)?[:\.]?\s*)?(\d+)[\.:\)]\s*(.+)',
        re.IGNORECASE | re.MULTILINE
    )
    CHOICE_PATTERN = re.compile(
        r'^([A-F])[\.\):\s]+(.+?)(?=^[A-F][\.\):\s]|$)',
        re.MULTILINE | re.DOTALL
    )
    ANSWER_PATTERNS = [
        # Match "Answer: B" or "Answer:A,B" - stop at newline to avoid capturing Explanation
        re.compile(r'Answer[:\s]+([A-F](?:[,\s]*[A-F])*?)(?=\n|Explanation|Reference|$)', re.IGNORECASE),
        # Match "Correct Answer: A" format
        re.compile(r'Correct\s+Answer[s]?[:\s]+([A-F](?:[,\s]*[A-F])*)', re.IGNORECASE),
        # Simple "Answer: A" on same line
        re.compile(r'Answer[:\s]+([A-F])\b', re.IGNORECASE),
        # Markdown format **Answer**: A
        re.compile(r'\*\*Answer[s]?\*\*[:\s]*([A-F](?:[,\s]*[A-F])*)', re.IGNORECASE),
    ]
    EXPLANATION_PATTERN = re.compile(
        r'(?:Explanation|Reference|Note)[:\s]*(.+?)(?=Q\d+|QUESTION|$)',
        re.IGNORECASE | re.DOTALL
    )
    
    def __init__(self, exhibits_dir: Optional[Path] = None):
        self.classifier = get_classifier()
        # Use config EXHIBITS_DIR (supports Railway volumes)
        if exhibits_dir is None:
            self.exhibits_dir = EXHIBITS_DIR
        else:
            self.exhibits_dir = exhibits_dir
        self.exhibits_dir.mkdir(parents=True, exist_ok=True)
    
    def get_file_hash(self, filepath: Path) -> str:
        """Calculate SHA256 hash of file."""
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def parse_pdf(self, filepath: Path) -> ParseReport:
        """Parse a PDF file and extract questions."""
        report = ParseReport(filename=filepath.name)
        
        try:
            text_by_page = self._extract_text(filepath)
        except Exception as e:
            logger.error(f"Failed to extract text from {filepath}: {e}")
            report.page_issues[0] = [f"Failed to read PDF: {str(e)}"]
            return report
        
        # Combine all text for processing
        full_text = "\n".join(text_by_page.values())
        
        # Extract questions
        questions = self._parse_questions(full_text, text_by_page)
        
        # Extract images from PDF and link to questions
        self._extract_and_link_images(filepath, questions, text_by_page)
        
        # Detect question series and assign IDs
        self._detect_question_series(questions)
        
        # Assign sequence numbers
        for idx, q in enumerate(questions, 1):
            q.sequence_number = idx
        
        # Classify domains and track stats
        seen_ids = set()
        for q in questions:
            report.total_questions += 1
            
            # Classify domain
            q.domain_id = self.classifier.classify(q.text)
            
            # Check for issues (skip for study questions)
            if q.question_type != "study":
                if not q.correct_answers:
                    report.missing_answers += 1
                    q.issues.append("Missing correct answer")
                
                if len(q.choices) < 2:
                    report.broken_choices += 1
                    q.issues.append("Less than 2 choices")
                
                # Check for suspiciously short choices (likely truncated)
                for choice in q.choices:
                    choice_text = choice.get('text', '')
                    # Flag if choice is very short or ends with suspicious patterns
                    if len(choice_text) < 10:
                        q.issues.append(f"Choice {choice['label']} is suspiciously short: '{choice_text}'")
                    elif choice_text.endswith(('?', 'and then', 'and', 'the', 'to', 'as the', 'from')):
                        q.issues.append(f"Choice {choice['label']} may be truncated: ends with '{choice_text[-20:]}'")
            
            if q.stable_id in seen_ids:
                report.duplicates += 1
                q.issues.append("Duplicate question")
            else:
                seen_ids.add(q.stable_id)
            
            if q.is_valid:
                report.valid_questions += 1
            
            report.questions.append(q)
        
        return report
    
    def _extract_text(self, filepath: Path) -> Dict[int, str]:
        """Extract text from PDF using PyMuPDF for better word spacing."""
        text_by_page = {}
        
        # Use PyMuPDF with text blocks for better spacing
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(filepath)
            for i, page in enumerate(doc, 1):
                # Extract tables first
                tables_text = self._extract_tables_from_page(page)
                
                # Use "text" mode which preserves word spacing better
                text = page.get_text("text", sort=True)
                
                # Insert table text at appropriate locations
                if tables_text:
                    text = self._merge_tables_with_text(text, tables_text)
                
                text_by_page[i] = text
            doc.close()
            if text_by_page:
                return text_by_page
        except ImportError:
            logger.warning("PyMuPDF not available, trying pdfplumber")
        except Exception as e:
            logger.warning(f"PyMuPDF failed: {e}, trying pdfplumber")
        
        # Fallback to pdfplumber (also has table support)
        try:
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                for i, page in enumerate(pdf.pages, 1):
                    # Extract tables first
                    tables_text = self._extract_tables_pdfplumber(page)
                    
                    text = page.extract_text(
                        x_tolerance=3,
                        y_tolerance=3,
                    ) or ""
                    
                    # Insert table text
                    if tables_text:
                        text = self._merge_tables_with_text(text, tables_text)
                    
                    text_by_page[i] = text
            return text_by_page
        except ImportError:
            raise ImportError("Neither PyMuPDF nor pdfplumber is available")
        except Exception as e:
            raise RuntimeError(f"Failed to extract text with pdfplumber: {e}")
    
    def _extract_tables_from_page(self, page) -> List[str]:
        """Extract tables from a PyMuPDF page and format as text."""
        tables_text = []
        try:
            # PyMuPDF 1.23+ has find_tables()
            tabs = page.find_tables()
            for tab in tabs:
                table_data = tab.extract()
                if table_data and len(table_data) > 0:
                    formatted = self._format_table_as_text(table_data)
                    if formatted:
                        tables_text.append(formatted)
        except AttributeError:
            # Older PyMuPDF version without find_tables
            pass
        except Exception as e:
            logger.debug(f"Table extraction failed: {e}")
        return tables_text
    
    def _extract_tables_pdfplumber(self, page) -> List[str]:
        """Extract tables from a pdfplumber page and format as text."""
        tables_text = []
        try:
            tables = page.extract_tables()
            for table_data in tables:
                if table_data and len(table_data) > 0:
                    formatted = self._format_table_as_text(table_data)
                    if formatted:
                        tables_text.append(formatted)
        except Exception as e:
            logger.debug(f"Table extraction failed: {e}")
        return tables_text
    
    def _format_table_as_text(self, table_data: List[List]) -> Optional[str]:
        """Format table data as readable text with borders."""
        if not table_data or len(table_data) < 2:
            return None
        
        # Filter out empty rows and clean cells
        cleaned_rows = []
        for row in table_data:
            if row:
                cleaned_row = [str(cell).strip() if cell else "" for cell in row]
                # Skip rows that are completely empty
                if any(cleaned_row):
                    cleaned_rows.append(cleaned_row)
        
        if len(cleaned_rows) < 2:
            return None
        
        # Calculate column widths
        num_cols = max(len(row) for row in cleaned_rows)
        col_widths = [0] * num_cols
        
        for row in cleaned_rows:
            for i, cell in enumerate(row):
                if i < num_cols:
                    col_widths[i] = max(col_widths[i], len(cell))
        
        # Build formatted table
        lines = []
        separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
        
        for row_idx, row in enumerate(cleaned_rows):
            # Pad row to have correct number of columns
            while len(row) < num_cols:
                row.append("")
            
            # Format row
            cells = [f" {row[i]:<{col_widths[i]}} " for i in range(num_cols)]
            line = "|" + "|".join(cells) + "|"
            
            # Add separator before first row and after header
            if row_idx == 0:
                lines.append(separator)
            lines.append(line)
            if row_idx == 0:  # Header separator
                lines.append(separator)
        
        lines.append(separator)
        return "\n".join(lines)
    
    def _merge_tables_with_text(self, text: str, tables_text: List[str]) -> str:
        """Merge extracted tables with page text."""
        if not tables_text:
            return text
        
        # Add tables at the end of text with clear markers
        # In practice, tables should be inserted based on their position,
        # but for simplicity we append them after relevant context
        table_section = "\n\n" + "\n\n".join(tables_text)
        
        # Try to find a good insertion point (after "following" mentions tables)
        patterns = [
            r'(following\s+(?:users|resources|virtual machines|storage accounts|subscriptions)[^:]*:)',
            r'(contains\s+the\s+following[^:]*:)',
            r'(shown\s+in\s+the\s+following[^:]*:)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                insert_pos = match.end()
                return text[:insert_pos] + table_section + text[insert_pos:]
        
        # Default: insert tables after first paragraph
        first_para_end = text.find('\n\n')
        if first_para_end > 0:
            return text[:first_para_end] + table_section + text[first_para_end:]
        
        return text + table_section
    
    def _parse_questions(self, full_text: str, text_by_page: Dict[int, str]) -> List[ParsedQuestion]:
        """Parse questions from extracted text."""
        questions = []
        
        # Split into question blocks - look for QUESTION markers or numbered questions
        question_blocks = self._split_into_blocks(full_text)
        
        for block in question_blocks:
            try:
                q = self._parse_single_question(block, text_by_page)
                if q and (q.text or q.choices):
                    questions.append(q)
            except Exception as e:
                logger.warning(f"Failed to parse question block: {e}")
        
        return questions
    
    def _split_into_blocks(self, text: str) -> List[str]:
        """Split text into question blocks."""
        # Try splitting by Q1, Q2 format first (common in exam PDFs)
        blocks = re.split(r'(?=^Q\d+\n)', text, flags=re.MULTILINE)
        
        if len(blocks) < 2:
            # Try splitting by QUESTION markers
            blocks = re.split(r'(?=QUESTION\s*(?:NO)?[:\.]?\s*\d+)', text, flags=re.IGNORECASE)
        
        if len(blocks) < 2:
            # Try splitting by numbered questions
            blocks = re.split(r'(?=^\d+[\.\)]\s+)', text, flags=re.MULTILINE)
        
        return [b.strip() for b in blocks if b.strip()]
    
    def _parse_single_question(self, block: str, text_by_page: Dict[int, str]) -> Optional[ParsedQuestion]:
        """Parse a single question from a text block."""
        # Extract question number from block (e.g., Q230)
        question_number = 0
        q_num_match = re.match(r'^Q(\d+)', block, re.MULTILINE)
        if q_num_match:
            question_number = int(q_num_match.group(1))
        
        # Check if this is a DRAG DROP or HOTSPOT question (study mode)
        block_upper = block.upper()
        is_study = 'DRAGDROP' in block_upper or 'DRAG DROP' in block_upper or 'HOTSPOT' in block_upper
        
        # Extract question text
        question_text = self._extract_question_text(block)
        if not question_text:
            return None
        
        # Extract explanation (needed for study questions)
        explanation = self._extract_explanation(block)
        
        # For study questions, we need text + explanation
        if is_study:
            # Clean up study question text - remove interactive instructions and headers
            question_text = re.sub(r'^DRAGDROP\s*', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'^HOTSPOT\s*', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'Select and Place[:\s]*', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'Hot Area[:\s]*', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'Answer by dragging.*?answer area\.?', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'To answer,.*?answer area\.?', '', question_text, flags=re.IGNORECASE)
            question_text = re.sub(r'NOTE:.*?point\.?', '', question_text, flags=re.IGNORECASE)
            
            # Remove embedded "Answer: Explanation:" text that appears in the question
            question_text = re.sub(r'Answer:\s*Explanation:.*$', '', question_text, flags=re.IGNORECASE | re.DOTALL)
            question_text = re.sub(r'\?\s*Answer:.*$', '?', question_text, flags=re.IGNORECASE | re.DOTALL)
            
            # Better word separation for PDFs without spaces
            question_text = self._fix_word_spacing(question_text)
            
            # Try to get explanation - look for clean Explanation section after Answer:
            expl_match = re.search(r'Explanation[:\s]+([A-Z][^Q]+?)(?=Q\d+|$)', block, re.DOTALL)
            if expl_match:
                explanation = expl_match.group(1).strip()
                explanation = self._fix_word_spacing(explanation)
                # Only use if it's meaningful and doesn't repeat the question
                if len(explanation) < 50 or question_text[:30].lower() in explanation[:100].lower():
                    explanation = None
            
            # Try Reference URL as explanation
            if not explanation:
                ref_match = re.search(r'Reference[:\s]*(https?://[^\s]+)', block, re.IGNORECASE)
                if ref_match:
                    explanation = f"Reference: {ref_match.group(1)}"
            
            # Use helpful fallback based on question type
            if not explanation:
                if 'DRAGDROP' in block_upper or 'DRAG DROP' in block_upper:
                    explanation = "📋 DRAG & DROP: This question requires matching or ordering items. Focus on understanding the relationships between Azure components mentioned in the scenario."
                else:
                    explanation = "🎯 HOTSPOT: This question requires selecting areas on a diagram. Focus on understanding the Azure portal interface and configuration options mentioned."
            
            return ParsedQuestion(
                text=question_text,
                choices=[],  # No choices for study questions
                correct_answers=[],  # No selectable answers
                explanation=explanation,
                question_type="study",
                source_page=question_number,  # Use question number instead of page
            )
        
        # Standard multiple choice parsing
        choices = self._extract_choices(block)
        question_type = self._determine_type(question_text, choices)
        correct_answers = self._extract_answers(block)
        
        return ParsedQuestion(
            text=question_text,
            choices=choices,
            correct_answers=correct_answers,
            explanation=explanation,
            question_type=question_type,
            source_page=question_number,  # Use question number instead of page
        )
    
    def _extract_question_text(self, block: str) -> str:
        """Extract the question text from a block."""
        # Remove Q# or QUESTION header
        text = re.sub(r'^Q\d+\n', '', block, flags=re.MULTILINE)
        text = re.sub(r'^QUESTION\s*(?:NO)?[:\.]?\s*\d+[:\.\s]*', '', text, flags=re.IGNORECASE)
        
        # Find where choices start (handles both "A. text" and "A.text" formats)
        choice_match = re.search(r'^[A-F][\.\)]', text, re.MULTILINE)
        if choice_match:
            text = text[:choice_match.start()]
        
        # Apply comprehensive word spacing fix with paragraph preservation
        text = self._fix_word_spacing_preserve_paragraphs(text)
        
        return text
    
    def _extract_choices(self, block: str) -> List[Dict[str, str]]:
        """Extract answer choices from a block."""
        choices = []
        
        # Normalize excessive line breaks - replace all \n with space
        normalized_block = block.replace('\n', ' ')
        # Clean up multiple spaces
        normalized_block = re.sub(r'\s+', ' ', normalized_block)
        
        # Find all choice markers and their positions
        choice_positions = []
        for label in 'ABCDEF':
            # Look for " A." or " A)" (space before choice letter)
            # Also match at start of string or after punctuation
            pattern = rf'(?:^|\s|[.!?])({label}[\.\)])'
            for match in re.finditer(pattern, normalized_block):
                # Position after the space/punct and label
                choice_positions.append((match.start(), label, match.end()))
        
        # Sort by position
        choice_positions.sort()
        
        # Extract text between choice markers
        for i, (start, label, text_start) in enumerate(choice_positions):
            # Determine end position
            if i + 1 < len(choice_positions):
                end = choice_positions[i + 1][0]
            else:
                # Last choice - find end markers
                end_match = re.search(
                    r'\b(?:Answer:|Explanation:|Reference:|Correct\s+Answer|Q\d+)',
                    normalized_block[text_start:],
                    re.IGNORECASE
                )
                if end_match:
                    end = text_start + end_match.start()
                else:
                    end = len(normalized_block)
            
            # Extract and clean choice text
            choice_text = normalized_block[text_start:end].strip()
            
            # Apply word spacing fix
            choice_text = self._fix_word_spacing(choice_text)
            
            # Final cleanup
            choice_text = re.sub(r'\s+', ' ', choice_text).strip()
            
            if choice_text:
                choices.append({"label": label, "text": choice_text})
        
        return choices
    
    def _determine_type(self, question_text: str, choices: List[Dict]) -> str:
        """Determine the question type."""
        text_lower = question_text.lower()
        
        # Check for multi-select indicators
        multi_indicators = [
            "select all", "choose all", "select two", "select three",
            "which two", "which three", "(choose two)", "(choose three)",
            "select the correct answers", "correct answers are"
        ]
        if any(ind in text_lower for ind in multi_indicators):
            return "multi"
        
        # Check for true/false
        if len(choices) == 2:
            choice_texts = [c["text"].lower() for c in choices]
            if set(choice_texts) == {"true", "false"} or set(choice_texts) == {"yes", "no"}:
                return "truefalse"
        
        return "single"
    
    def _extract_answers(self, block: str) -> List[str]:
        """Extract correct answer(s) from a block."""
        for pattern in self.ANSWER_PATTERNS:
            match = pattern.search(block)
            if match:
                answer_text = match.group(1).upper()
                # Extract individual letters
                answers = re.findall(r'[A-F]', answer_text)
                if answers:
                    return answers
        return []
    
    def _extract_explanation(self, block: str) -> Optional[str]:
        """Extract explanation text from a block."""
        match = self.EXPLANATION_PATTERN.search(block)
        if match:
            explanation = match.group(1).strip()
            explanation = re.sub(r'\s+', ' ', explanation)
            if len(explanation) > 20:  # Minimum meaningful explanation
                return explanation[:2000]  # Limit length
        return None
    
    def _fix_word_spacing_preserve_paragraphs(self, text: str) -> str:
        """Fix word spacing while preserving paragraph structure."""
        if not text:
            return text
        
        # Split into lines
        lines = text.split('\n')
        processed_lines = []
        current_paragraph = []
        
        for line in lines:
            line = line.strip()
            
            # Empty line = paragraph break
            if not line:
                if current_paragraph:
                    # Join current paragraph and process it
                    para_text = ' '.join(current_paragraph)
                    para_text = self._fix_word_spacing(para_text)
                    processed_lines.append(para_text)
                    current_paragraph = []
                continue
            
            # Check if this line starts a new logical section
            # (starts with "Note:", "Solution:", "You", question keywords, etc.)
            is_section_start = bool(re.match(
                r'^(Note:|Solution:|After you|You |Your |From |To answer|Each |Some |Does |What |Which |How )',
                line,
                re.IGNORECASE
            ))
            
            if is_section_start and current_paragraph:
                # Finish previous paragraph
                para_text = ' '.join(current_paragraph)
                para_text = self._fix_word_spacing(para_text)
                processed_lines.append(para_text)
                current_paragraph = [line]
            else:
                current_paragraph.append(line)
        
        # Process remaining paragraph
        if current_paragraph:
            para_text = ' '.join(current_paragraph)
            para_text = self._fix_word_spacing(para_text)
            processed_lines.append(para_text)
        
        # Join with double newlines for readability
        return '\n\n'.join(processed_lines)
    
    def _fix_word_spacing(self, text: str) -> str:
        """Fix word spacing for PDFs with concatenated or split words."""
        if not text:
            return text
        
        # First pass: Add space before any uppercase letter that follows a lowercase letter
        text = re.sub(r'([a-z])([A-Z])', r'\1 \2', text)
        
        # Add space after punctuation followed by letters
        text = re.sub(r'([.!?,:;])([A-Za-z])', r'\1 \2', text)
        
        # Add space before opening parenthesis if preceded by letter
        text = re.sub(r'([a-zA-Z])\(', r'\1 (', text)
        
        # Add space after closing parenthesis if followed by letter
        text = re.sub(r'\)([a-zA-Z])', r') \1', text)
        
        # Expand common abbreviations used in exam questions
        # Use word boundaries to avoid changing parts of other words
        abbreviations = [
            (r'\bqis\b', 'question is'),
            (r'\bqin\b', 'question in'),
            (r'\bqs\b', 'questions'),
            (r'\bqsets\b', 'question sets'),
            (r'\bqset\b', 'question set'),
        ]
        for pattern, replacement in abbreviations:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Fix common multi-word patterns (only for truly concatenated words)
        patterns = [
            (r'Youhave', 'You have'),
            (r'Youneed', 'You need'),
            (r'Youare', 'You are'),
            (r'Youplan', 'You plan'),
            (r'Youwant', 'You want'),
            (r'Whatshould', 'What should'),
            (r'Whichof', 'Which of'),
            (r'tothe', 'to the'),
            (r'ofthe', 'of the'),
            (r'inthe', 'in the'),
            (r'onthe', 'on the'),
            (r'fromthe', 'from the'),
            (r'allthe', 'all the'),
            (r'thatthe', 'that the'),
            (r'isthe', 'is the'),
            (r'forthe', 'for the'),
            (r'andthe', 'and the'),
            (r'thata', 'that a'),
            (r'tocreate', 'to create'),
            (r'toensure', 'to ensure'),
            (r'tomake', 'to make'),
            (r'toreference', 'to reference'),
            (r'todeploy', 'to deploy'),
            (r'toachieve', 'to achieve'),
            (r'shouldyou', 'should you'),
            (r'doyou', 'do you'),
            (r'canyou', 'can you'),
        ]
        for pattern, replacement in patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def _find_source_page(self, question_text: str, text_by_page: Dict[int, str]) -> int:
        """Find which page contains the question."""
        if not question_text:
            return 0
        
        # Use first 50 chars as search string
        search_text = question_text[:50].lower()
        
        for page_num, page_text in text_by_page.items():
            if search_text in page_text.lower():
                return page_num
        
        return 0
    
    def _find_pdf_page_for_question(self, question_text: str, text_by_page: Dict[int, str]) -> int:
        """Find the actual PDF page containing a question using longer, unique text match."""
        if not question_text:
            return 0
        
        # Normalize whitespace in search text for better matching
        search_text = re.sub(r'\s+', ' ', question_text[:200]).lower()
        
        for page_num, page_text in text_by_page.items():
            # Normalize page text whitespace too
            normalized_page = re.sub(r'\s+', ' ', page_text).lower()
            if search_text in normalized_page:
                return page_num
        
        # Fallback: try with first 100 chars
        search_text = re.sub(r'\s+', ' ', question_text[:100]).lower()
        for page_num, page_text in text_by_page.items():
            normalized_page = re.sub(r'\s+', ' ', page_text).lower()
            if search_text in normalized_page:
                return page_num
        
        return 0
    
    def _extract_and_link_images(self, filepath: Path, questions: List[ParsedQuestion], text_by_page: Dict[int, str]):
        """Extract images from PDF and link them to questions with exhibits or table images."""
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.warning("PyMuPDF not available - skipping image extraction")
            return
        
        try:
            doc = fitz.open(filepath)
            
            # Track which questions reference exhibits
            exhibit_keywords = [
                "following exhibit", "shown in the following", "as shown in",
                "following diagram", "following image", "exhibit", "shown below"
            ]
            
            # Keywords that suggest tabular data is expected
            table_keywords = [
                "following users", "following resources", "following table",
                "following virtual machines", "following storage accounts",
                "following subscriptions", "contains the following",
                "following information", "following configuration",
                "following azure", "following settings"
            ]
            
            for q in questions:
                # Check if question references an exhibit or table data
                q_text_lower = q.text.lower()
                has_exhibit = any(keyword in q_text_lower for keyword in exhibit_keywords)
                has_table = any(keyword in q_text_lower for keyword in table_keywords)
                
                if not has_exhibit and not has_table:
                    continue
                
                # Find the actual PDF page containing this question
                # (source_page is the question number, not the PDF page number)
                pdf_page_num = self._find_pdf_page_for_question(q.text, text_by_page)
                if not pdf_page_num or pdf_page_num == 0:
                    continue
                
                # Try to extract images from the page (0-indexed in PyMuPDF)
                page = doc[pdf_page_num - 1]
                image_list = page.get_images(full=True)
                
                if not image_list:
                    # Try previous page (exhibit might be on page before question)
                    if pdf_page_num > 1:
                        page = doc[pdf_page_num - 2]
                        image_list = page.get_images(full=True)
                
                # Save the first sizeable image found
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)
                    
                    # Skip tiny icons/logos (less than 5KB)
                    if len(image_bytes) < 5000:
                        continue
                    
                    # For table-type images: accept wide, short images (typical table dimensions)
                    # These are often 400-800px wide and 100-300px tall
                    is_table_like = width > 300 and height > 50 and width / max(height, 1) > 1.5
                    
                    # For exhibit images: require larger size (10KB+)
                    is_exhibit = len(image_bytes) >= 10000
                    
                    if not is_table_like and not is_exhibit:
                        continue
                    
                    # Generate unique filename using stable_id for uniqueness
                    stable_suffix = q.stable_id[:8] if hasattr(q, 'stable_id') else ''
                    filename = f"q{q.source_page}_{stable_suffix}_img{img_index}.{image_ext}"
                    filepath_img = self.exhibits_dir / filename
                    
                    # Save image
                    with open(filepath_img, "wb") as img_file:
                        img_file.write(image_bytes)
                    
                    # Link to question (relative path for web serving)
                    q.exhibit_image = f"/static/exhibits/{filename}"
                    img_type = "table" if is_table_like else "exhibit"
                    logger.info(f"Extracted {img_type} image for Q{q.source_page}: {filename} ({width}x{height})")
                    break  # Only save first meaningful image per question
            
            doc.close()
        except Exception as e:
            logger.error(f"Failed to extract images from {filepath}: {e}")
    
    def _detect_question_series(self, questions: List[ParsedQuestion]):
        """Detect related questions (series) and assign series_id.
        
        Series are detected by:
        1. Explicit "Note: This question is part of a series" markers
        2. Questions that share identical scenario text (same table, same setup)
        """
        # Patterns that indicate a question is part of a series
        series_patterns = [
            r"note:\s*this question is part of a series",
            r"note:\s*the question is included in a number of questions",
            r"part of a series of questions",
            r"identical set-up",
            r"depicts the identical",
            r"same scenario",
            r"questions that share the same",
            r"questions that present the same scenario",
        ]
        
        # First pass: detect explicit series markers and extract core scenarios
        series_scenarios = {}  # {scenario_hash: series_id}
        
        for q in questions:
            q_text_lower = q.text.lower()
            
            # Check if this question has explicit series marker
            has_series_marker = any(
                re.search(pattern, q_text_lower, re.IGNORECASE) 
                for pattern in series_patterns
            )
            
            if has_series_marker:
                # Extract the core scenario (after the Note: section)
                # This is typically the setup that's shared across series questions
                core_scenario = self._extract_core_scenario(q.text)
                scenario_hash = hashlib.sha256(core_scenario.encode()).hexdigest()[:12]
                
                if scenario_hash not in series_scenarios:
                    series_scenarios[scenario_hash] = scenario_hash
                    logger.info(f"Detected series at Q{q.source_page}: {scenario_hash}")
                
                q.series_id = series_scenarios[scenario_hash]
        
        # Second pass: find questions that share the same core scenario
        for q in questions:
            if q.series_id:  # Already assigned
                continue
            
            core_scenario = self._extract_core_scenario(q.text)
            scenario_hash = hashlib.sha256(core_scenario.encode()).hexdigest()[:12]
            
            # Check if this scenario matches any known series
            if scenario_hash in series_scenarios:
                q.series_id = series_scenarios[scenario_hash]
                logger.info(f"Linked Q{q.source_page} to series {scenario_hash}")
    
    def _extract_core_scenario(self, text: str) -> str:
        """Extract the core scenario text from a question for series matching.
        
        Removes the "Note:" header and solution-specific text to get the
        shared scenario that's common across series questions.
        """
        # Remove the "Note: This question is part of a series..." header
        text = re.sub(
            r'^Note:.*?(?=You have|You are|Your company|A company)',
            '',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Remove "After you answer..." warning text
        text = re.sub(
            r'After you answer a question in this section.*?review screen\.?\s*',
            '',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )
        
        # Extract up to the "Solution:" or "Does that meet" part
        # This gives us the shared scenario without the solution
        solution_match = re.search(r'Solution:|Does that meet|What should you', text, re.IGNORECASE)
        if solution_match:
            text = text[:solution_match.start()]
        
        # Normalize variations for better matching
        # Remove minor wording differences
        text = re.sub(r"Your company's Azure solution", "Your company", text, flags=re.IGNORECASE)
        text = re.sub(r"Your company's", "Your company", text, flags=re.IGNORECASE)
        text = re.sub(r"makes use of", "uses", text, flags=re.IGNORECASE)
        
        # Clean and normalize
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Take first 200 chars as scenario fingerprint (shorter for better matching)
        return text[:200]


def get_demo_questions() -> List[ParsedQuestion]:
    """Generate demo questions when no PDFs are available."""
    classifier = get_classifier()
    
    demos = [
        ParsedQuestion(
            text="You need to create a new Azure subscription. What should you use?",
            choices=[
                {"label": "A", "text": "Azure portal"},
                {"label": "B", "text": "Azure PowerShell"},
                {"label": "C", "text": "Azure CLI"},
                {"label": "D", "text": "Azure Resource Manager templates"},
            ],
            correct_answers=["A"],
            explanation="New subscriptions are typically created through the Azure portal or programmatically via the Azure Account API.",
            question_type="single",
            domain_id="identity-governance",
            source_page=1,
        ),
        ParsedQuestion(
            text="Which Azure storage redundancy option replicates data across multiple availability zones?",
            choices=[
                {"label": "A", "text": "Locally redundant storage (LRS)"},
                {"label": "B", "text": "Zone-redundant storage (ZRS)"},
                {"label": "C", "text": "Geo-redundant storage (GRS)"},
                {"label": "D", "text": "Read-access geo-redundant storage (RA-GRS)"},
            ],
            correct_answers=["B"],
            explanation="Zone-redundant storage (ZRS) replicates data synchronously across three Azure availability zones in the primary region.",
            question_type="single",
            domain_id="storage",
            source_page=1,
        ),
        ParsedQuestion(
            text="You need to deploy a virtual machine that requires the lowest possible latency to an existing VM. What should you use?",
            choices=[
                {"label": "A", "text": "Availability set"},
                {"label": "B", "text": "Availability zone"},
                {"label": "C", "text": "Proximity placement group"},
                {"label": "D", "text": "Virtual machine scale set"},
            ],
            correct_answers=["C"],
            explanation="Proximity placement groups place VMs physically close together in the same datacenter to minimize latency.",
            question_type="single",
            domain_id="compute",
            source_page=1,
        ),
        ParsedQuestion(
            text="Which of the following can be used to filter network traffic between subnets? (Choose two)",
            choices=[
                {"label": "A", "text": "Network security groups (NSG)"},
                {"label": "B", "text": "Application security groups (ASG)"},
                {"label": "C", "text": "Azure Firewall"},
                {"label": "D", "text": "Azure Load Balancer"},
            ],
            correct_answers=["A", "C"],
            explanation="NSGs and Azure Firewall can filter traffic between subnets. ASGs are used to group VMs, and Load Balancer distributes traffic.",
            question_type="multi",
            domain_id="networking",
            source_page=1,
        ),
        ParsedQuestion(
            text="You need to configure alerts for when a VM's CPU usage exceeds 80%. Which Azure service should you use?",
            choices=[
                {"label": "A", "text": "Azure Monitor"},
                {"label": "B", "text": "Azure Advisor"},
                {"label": "C", "text": "Azure Service Health"},
                {"label": "D", "text": "Azure Activity Log"},
            ],
            correct_answers=["A"],
            explanation="Azure Monitor provides metric-based alerting for Azure resources including virtual machines.",
            question_type="single",
            domain_id="monitoring",
            source_page=1,
        ),
    ]
    
    return demos

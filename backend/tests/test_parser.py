"""Tests for the PDF parser module."""
import pytest
from app.services.parser import PDFParser, ParsedQuestion, get_demo_questions
from app.services.domain_classifier import DomainClassifier, get_classifier


class TestDomainClassifier:
    """Tests for domain classification."""
    
    def test_classify_storage_question(self):
        """Test classification of storage-related questions."""
        classifier = get_classifier()
        text = "Which storage redundancy option should you use for blob containers?"
        domain = classifier.classify(text)
        assert domain == "storage"
    
    def test_classify_compute_question(self):
        """Test classification of compute-related questions."""
        classifier = get_classifier()
        text = "You need to deploy a virtual machine with high availability."
        domain = classifier.classify(text)
        assert domain == "compute"
    
    def test_classify_networking_question(self):
        """Test classification of networking-related questions."""
        classifier = get_classifier()
        text = "Configure the network security group to allow traffic on port 443."
        domain = classifier.classify(text)
        assert domain == "networking"
    
    def test_classify_monitoring_question(self):
        """Test classification of monitoring-related questions."""
        classifier = get_classifier()
        text = "Set up Azure Monitor alerts for the backup policy."
        domain = classifier.classify(text)
        assert domain == "monitoring"
    
    def test_classify_identity_question(self):
        """Test classification of identity-related questions."""
        classifier = get_classifier()
        text = "You need to configure RBAC role assignments for users in Azure AD."
        domain = classifier.classify(text)
        assert domain == "identity-governance"
    
    def test_get_domain_name(self):
        """Test getting domain names."""
        classifier = get_classifier()
        name = classifier.get_domain_name("storage")
        assert name == "Implement and manage storage"


class TestParsedQuestion:
    """Tests for ParsedQuestion dataclass."""
    
    def test_stable_id_generation(self):
        """Test that stable IDs are generated consistently."""
        q1 = ParsedQuestion(
            text="Test question?",
            choices=[{"label": "A", "text": "Answer A"}],
            correct_answers=["A"]
        )
        q2 = ParsedQuestion(
            text="Test question?",
            choices=[{"label": "A", "text": "Answer A"}],
            correct_answers=["A"]
        )
        assert q1.stable_id == q2.stable_id
    
    def test_is_valid(self):
        """Test validation of parsed questions."""
        valid = ParsedQuestion(
            text="Question?",
            choices=[{"label": "A", "text": "A"}, {"label": "B", "text": "B"}],
            correct_answers=["A"]
        )
        assert valid.is_valid
        
        invalid = ParsedQuestion(
            text="Question?",
            choices=[],
            correct_answers=[]
        )
        assert not invalid.is_valid


class TestDemoQuestions:
    """Tests for demo question generation."""
    
    def test_demo_questions_count(self):
        """Test that demo questions are generated."""
        demos = get_demo_questions()
        assert len(demos) >= 5
    
    def test_demo_questions_validity(self):
        """Test that all demo questions are valid."""
        demos = get_demo_questions()
        for q in demos:
            assert q.is_valid
            assert q.text
            assert len(q.choices) >= 2
            assert len(q.correct_answers) >= 1
    
    def test_demo_questions_domains(self):
        """Test that demo questions cover multiple domains."""
        demos = get_demo_questions()
        domains = {q.domain_id for q in demos}
        assert len(domains) >= 3  # At least 3 different domains


class TestPDFParser:
    """Tests for PDF parser functionality."""
    
    def test_determine_single_type(self):
        """Test single-select question type detection."""
        parser = PDFParser()
        choices = [
            {"label": "A", "text": "Option A"},
            {"label": "B", "text": "Option B"},
            {"label": "C", "text": "Option C"},
        ]
        qtype = parser._determine_type("Which option should you choose?", choices)
        assert qtype == "single"
    
    def test_determine_multi_type(self):
        """Test multi-select question type detection."""
        parser = PDFParser()
        choices = [
            {"label": "A", "text": "Option A"},
            {"label": "B", "text": "Option B"},
        ]
        qtype = parser._determine_type("Select all that apply. Which two options?", choices)
        assert qtype == "multi"
    
    def test_determine_truefalse_type(self):
        """Test true/false question type detection."""
        parser = PDFParser()
        choices = [
            {"label": "A", "text": "True"},
            {"label": "B", "text": "False"},
        ]
        qtype = parser._determine_type("Is this statement correct?", choices)
        assert qtype == "truefalse"
    
    def test_extract_answers_single(self):
        """Test extracting single correct answer."""
        parser = PDFParser()
        block = "Question text\nA. Option A\nB. Option B\nAnswer: B"
        answers = parser._extract_answers(block)
        assert answers == ["B"]
    
    def test_extract_answers_multiple(self):
        """Test extracting multiple correct answers."""
        parser = PDFParser()
        block = "Question text\nCorrect Answers: A, C"
        answers = parser._extract_answers(block)
        assert set(answers) == {"A", "C"}

"""Tests for API endpoints."""
import pytest
from app.models import Question, DomainStats


class TestHealthEndpoint:
    """Tests for health check endpoint."""
    
    def test_health_check(self, client):
        """Test health endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "AZ-104 Exam Simulator"
        assert data["status"] == "running"


class TestImportEndpoints:
    """Tests for import-related endpoints."""
    
    def test_import_status_empty_db(self, client):
        """Test import status when database is empty."""
        response = client.get("/api/import/status")
        assert response.status_code == 200
        data = response.json()
        assert data["questions_in_db"] == 0
        assert data["needs_import"] == True
    
    def test_scan_no_pdfs(self, client):
        """Test scan when no PDFs exist (should offer demo data)."""
        response = client.post("/api/import/scan")
        assert response.status_code == 200
        data = response.json()
        # Should offer demo questions when no PDFs
        assert data["needs_import"] == True


class TestDashboardEndpoints:
    """Tests for dashboard endpoints."""
    
    def test_dashboard_empty(self, client):
        """Test dashboard with no data."""
        response = client.get("/api/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert data["overview"]["total_questions"] == 0
        assert data["overview"]["total_sessions"] == 0
    
    def test_domains_endpoint(self, client):
        """Test domains listing."""
        response = client.get("/api/domains")
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
        assert len(data["domains"]) >= 5


class TestSessionEndpoints:
    """Tests for session endpoints."""
    
    def test_start_session_no_questions(self, client):
        """Test starting session with no questions."""
        response = client.post("/api/session/start", json={"mode": "random"})
        assert response.status_code == 400  # No questions available
    
    def test_start_session_with_questions(self, client, db):
        """Test starting session with questions in database."""
        # Add test questions
        for i in range(5):
            q = Question(
                stable_id=f"test_{i}",
                text=f"Test question {i}?",
                choices=[
                    {"label": "A", "text": "Option A"},
                    {"label": "B", "text": "Option B"},
                ],
                correct_answers=["A"],
                question_type="single",
                domain_id="storage",
            )
            db.add(q)
        
        # Add domain stats
        stats = DomainStats(
            domain_id="storage",
            domain_name="Implement and manage storage",
            total_questions=5,
        )
        db.add(stats)
        db.commit()
        
        # Start session
        response = client.post("/api/session/start", json={"mode": "random"})
        assert response.status_code == 200
        data = response.json()
        assert data["id"] > 0
        assert len(data["question_ids"]) == 5  # Only 5 questions available


class TestExportEndpoints:
    """Tests for export functionality."""
    
    def test_export_missed_csv_empty(self, client):
        """Test exporting missed questions when none exist."""
        response = client.get("/api/export/missed.csv")
        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

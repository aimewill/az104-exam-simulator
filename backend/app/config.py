"""Application configuration.

⚠️  CRITICAL: Do NOT change the default paths below!
    Local development paths:
    - Database: data/az104.db (NOT exam.db)
    - PDFs: pdfs/ at project root (NOT data/pdfs/)
    - Exhibits: backend/app/static/exhibits/ (NOT data/exhibits/)
    
    For Railway deployment, use environment variables instead.
"""
import os
from pathlib import Path

# Base paths - support Railway volumes via environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data directory for database
DATA_DIR = Path(os.environ.get("DATA_DIR", os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", str(BASE_DIR / "data"))))

# PDFs directory - root pdfs/ for local, configurable via env for Railway
# DEFAULT: {project}/pdfs/
PDFS_DIR = Path(os.environ.get("PDFS_DIR", str(BASE_DIR / "pdfs")))

# Exhibits directory - backend/app/static/exhibits/ for local
# DEFAULT: {project}/backend/app/static/exhibits/
EXHIBITS_DIR = Path(os.environ.get("EXHIBITS_DIR", str(BASE_DIR / "backend" / "app" / "static" / "exhibits")))

CONFIG_DIR = BASE_DIR / "config"

# Database - use DATABASE_URL env var or default to SQLite az104.db in data dir
# DEFAULT: sqlite:///{project}/data/az104.db
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'az104.db'}")

# Exam settings
EXAM_QUESTION_COUNT = int(os.environ.get("EXAM_QUESTION_COUNT", "60"))
PASSING_SCORE = int(os.environ.get("PASSING_SCORE", "700"))
MAX_SCALED_SCORE = 1000

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PDFS_DIR.mkdir(parents=True, exist_ok=True)
EXHIBITS_DIR.mkdir(parents=True, exist_ok=True)

# Domain config path
DOMAINS_CONFIG_PATH = CONFIG_DIR / "domains.json"

# Server port (Railway provides PORT env var)
PORT = int(os.environ.get("PORT", "8000"))

# JWT Authentication
import secrets
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", secrets.token_urlsafe(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))

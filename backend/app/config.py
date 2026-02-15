"""Application configuration."""
import os
from pathlib import Path

# Base paths - support Railway volumes via environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Data directory: use RAILWAY_VOLUME_MOUNT_PATH or DATA_DIR env var, fallback to local
DATA_DIR = Path(os.environ.get("DATA_DIR", os.environ.get("RAILWAY_VOLUME_MOUNT_PATH", str(BASE_DIR / "data"))))
PDFS_DIR = Path(os.environ.get("PDFS_DIR", str(DATA_DIR / "pdfs")))
EXHIBITS_DIR = Path(os.environ.get("EXHIBITS_DIR", str(DATA_DIR / "exhibits")))
CONFIG_DIR = BASE_DIR / "config"

# Database - use DATABASE_URL env var or default to SQLite in data dir
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{DATA_DIR / 'exam.db'}")

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

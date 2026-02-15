"""FastAPI application entry point."""
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .database import init_db
from .config import EXHIBITS_DIR, PORT
from .routers import import_router, session, dashboard
from .frontend_mount import mount_frontend

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for the application."""
    # Startup
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    yield
    # Shutdown
    logger.info("Shutting down...")


app = FastAPI(
    title="Exam Simulator",
    description="Interactive exam simulator with PDF import, progress tracking, and multiple study modes",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for frontend
# In production (single service), frontend is served from same origin
# Allow all origins for flexibility during development and deployment
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for exhibit images (from config-based directory)
if EXHIBITS_DIR.exists():
    app.mount("/static/exhibits", StaticFiles(directory=str(EXHIBITS_DIR)), name="exhibits")

# Include routers
app.include_router(import_router.router)
app.include_router(session.router)
app.include_router(dashboard.router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# Mount built frontend for production (must be last to catch-all routes)
mount_frontend(app)

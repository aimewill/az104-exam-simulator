"""Mount built frontend for production single-service deployment."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse


def mount_frontend(app: FastAPI):
    """Mount the built frontend assets and serve SPA for all non-API routes."""
    # Frontend dist is at project_root/frontend/dist
    frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
    
    if not frontend_dist.exists():
        return  # No built frontend, skip (development mode)
    
    # Mount static assets (JS, CSS, images)
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="frontend-assets")
    
    # Serve index.html for SPA routing (catch-all for non-API routes)
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the SPA - return index.html for client-side routing."""
        # Don't intercept API routes
        if full_path.startswith("api/") or full_path.startswith("static/"):
            return None
        
        # Check if it's a real file in dist
        file_path = frontend_dist / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        
        # Return index.html for SPA routing
        return FileResponse(frontend_dist / "index.html")

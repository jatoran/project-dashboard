from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from .routers import projects, monitor, platforms

app = FastAPI(title="Gemini Project Dashboard")

# CORS - allow same-origin and dev server
origins = [
    "http://localhost:37453",  # Same origin (static frontend)
    "http://127.0.0.1:37453",
    "http://localhost:37452",  # Dev server
    "http://127.0.0.1:37452",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(projects.router, prefix="/api")
app.include_router(monitor.router, prefix="/api")
app.include_router(platforms.router, prefix="/api")


@app.get("/api/health")
def health_check():
    """Health check endpoint for system tray controller."""
    return {"status": "ok"}


@app.get("/command-palette.html")
def serve_command_palette():
    """Serve the command palette HTML for global hotkey."""
    palette_path = Path(__file__).parent / "command_palette.html"
    return FileResponse(palette_path)


# Mount static frontend (if built)
# This must come LAST since it catches all routes
frontend_dist = Path(__file__).parent / "frontend_dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")
else:
    @app.get("/")
    def read_root():
        return {
            "message": "Gemini Project Dashboard API is running",
            "note": "Frontend not built. Run 'npm run build' in frontend/ directory."
        }

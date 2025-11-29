# System Patterns

## Architecture
- **Structure:** Polyglot Monorepo.
    - `/frontend`: Next.js (App Router), Tailwind, Shadcn/UI.
    - `/backend`: Python, FastAPI, Uvicorn. Managed by `uv`.
- **Data Flow:** Frontend fetches project data from Backend API. Backend reads filesystem.

## Key Workflows

### 1. Project Discovery
- **Backend Service:** FastAPI endpoints (e.g., `GET /api/projects`).
- **Scanning:** Python scripts read `config/projects.json` using `pathlib` and scan directories.

### 2. Launchers
- Frontend sends command request: `POST /api/launch`
- Backend executes shell commands using `subprocess`.

### 3. Path Handling
- **Python Pathlib:** Robust path manipulation.
- **WSL Integration:** Python detects platform and constructs `cmd.exe /c` strings for Windows interop.

## Coding Standards
- **Frontend:** TypeScript (Strict), React Hooks.
- **Backend:** Python 3.11+, Type Hints (`mypy`), Pydantic models for API schemas.
- **API Style:** RESTful.

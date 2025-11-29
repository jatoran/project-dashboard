# Active Context

## Current Focus
Completing Phase 1 (Core Dashboard) and transitioning to maintenance/Phase 2.

## Recent History
- **Phase 1 Complete:**
    - Frontend: Next.js Dashboard (Port 37452).
    - Backend: FastAPI Service (Port 37453) running natively on Windows.
    - **Smart Scanner:** Implemented multi-stage heuristic detection for project types, FastAPI presence, and API ports (via Docker Compose, Markdown, Frontend Configs).
    - **Launchers:** Robust `os.startfile` for Explorer, `code` for VS Code (with Workspace support), and `wt.exe` logic for WSL (handling directory navigation).
    - **Docs:** Auto-generated Swagger/ReDoc links. Added **Markdown Scanner** (recursive) and **In-App Viewer**.

## System Status
- **Architecture:** Hybrid. Frontend (Next.js) proxies to Backend (FastAPI).
- **Runtime:** STRICTLY Windows Native (PowerShell) for execution, interacting with WSL data via file shares or mapped drives (`D:\...`).
- **Data:** Stored in `backend/data/projects.json`.
- **New Features:** 
    - Markdown docs viewing in modal, path copying.
    - **Multi-Tagging:** Intelligent scanning for Frameworks (React, Next.js, FastAPI, Django, etc.) and Infrastructure (Docker), displaying top tags instead of a single type.
    - **Copy Document Content:** Copy button next to Markdown files now copies the file's content (consistent with viewer modal).
    - **Frontend Monitor:** Auto-detects frontend ports (Node scripts, Docker Compose, Vite config, Markdown docs) and provides a real-time "App" status indicator with a launch link.
    - **Monorepo Support:** Scanner now recursively checks subdirectories (`frontend`, `client`, `web`, etc.) for `package.json` configurations to accurately tag projects and detect ports in nested structures.
    - **UI Refinement:** Fixed 5-column action grid to ensure consistent button layout. Code, Terminal, WSL, and Explorer are always visible, with App appearing in the 5th slot when available.
    - **Bug Fixes:** Fixed "Copy Document Content" button not triggering due to event bubbling issues; added explicit stopPropagation. Removed temporary "Copied!" feedback from project path copy action for cleaner UX.

## Active Decisions
- **Path Handling:** Input is expected to be Windows paths (`D:\projects\...`). WSL paths are supported via manual conversion logic in the launcher if needed, but `D:` is preferred.
- **Port Detection:** Heuristics prioritize `docker-compose.yml` > `README.md` > `Frontend Configs` > Default (8000).
- **Launch Logic:**
    - **Explorer:** `os.startfile(path)` (Most reliable).
    - **Terminal (WSL):** `wt.exe wsl.exe -e bash -c "cd 'path' && exec bash"` (Forces navigation regardless of profile defaults).
    - **VS Code:** Opens `.code-workspace` file if present, otherwise opens folder.

## Next Steps
- User testing and daily usage.
- Phase 2 (Future): Service Monitoring (Docker status, active ports).

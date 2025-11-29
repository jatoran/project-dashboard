# Active Context

## Current Focus
Completing Phase 1 (Core Dashboard) and transitioning to maintenance/Phase 2.

## Recent History
- **Phase 1 Complete:**
    - Frontend: Next.js Dashboard (Port 37452).
    - Backend: FastAPI Service (Port 37453) running natively on Windows.
    - **Smart Scanner:** Implemented multi-stage heuristic detection for project types, FastAPI presence, and API ports (via Docker Compose, Markdown, Frontend Configs).
    - **Launchers:** Robust `os.startfile` for Explorer, `code` for VS Code (with Workspace support), and `wt.exe` logic for WSL (handling directory navigation).
    - **Docs:** Auto-generated Swagger/ReDoc links for detected APIs.

## System Status
- **Architecture:** Hybrid. Frontend (Next.js) proxies to Backend (FastAPI).
- **Runtime:** STRICTLY Windows Native (PowerShell) for execution, interacting with WSL data via file shares or mapped drives (`D:\...`).
- **Data:** Stored in `backend/data/projects.json`.

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

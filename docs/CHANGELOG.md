# Changelog

## [1.1.0] - 2025-11-29
### Features
- **Documentation Hub:**
    - Recursively scans for `.md` files in root and `docs/` folders.
    - **In-App Viewer:** Opens Markdown files in a modal with syntax highlighting (via `react-markdown`).
    - **Quick Actions:** Copy file path button next to each document.

## [1.0.0] - 2025-11-29
### Features
- **Project Dashboard:** Centralized UI to manage local projects.
- **Smart Scanning:**
    - Auto-detects Node, Python, Rust, Docker.
    - Detects FastAPI and auto-generates Swagger/ReDoc links.
    - Heuristic Port Detection (Docker Compose, README, Frontend Configs).
    - VS Code Workspace file detection (`.code-workspace`).
- **Launchers:**
    - Open in **VS Code** (opens workspace if available).
    - Open in **Explorer**.
    - Open in **Windows Terminal (WSL)** (auto-navigates to path).
- **Project Management:** Add (by path) and Remove (Trash icon).

### Infrastructure
- **Split Architecture:** Next.js Frontend (37452) + FastAPI Backend (37453).
- **Windows Native:** Optimized for running on Windows while managing WSL files.
- **VS Code Automation:** `.vscode/tasks.json` for one-click startup.

### Fixes
- **Hybrid Pathing:** solved issues with `wslpath` not working on Windows by implementing manual path conversion.
- **WSL Navigation:** solved `wt.exe` profile overrides by using `bash -c ... exec bash` pattern.
- **Port Conflicts:** Moved off default 3000/8000 ports to avoid clashes with user projects.
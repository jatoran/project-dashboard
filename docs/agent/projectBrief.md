# Project Brief

## Vision
A "Project Dashboard" dashboard for a hybrid Windows/WSL development environment. The application serves as a centralized, read-only index for projects, allowing for quick navigation, documentation retrieval, and workspace launching.

## Core Requirements (Phase 1)
1.  **Centralized UI:** A clean, filterable interface to list projects.
2.  **Manual Indexing:** Projects are added by file path.
3.  **Dynamic Discovery:** The application reads the project directory to surface:
    - Project Type (Node, Python, Docker, etc.)
    - Documentation links (README, OpenAPI, Swagger).
    - Git status.
4.  **Launchers:**
    - Open Project Folder (Explorer).
    - Open Code Workspace (VS Code).
    - Open in WSL Terminal (Windows Terminal -> WSL -> `cd` -> `gemini` CLI).

## Future Scope (Phase 2 - Planned)
- **Service Monitoring:** Tracking status of Docker containers, Proxmox VMs, and local PC applications (Syncthing, Tailscale, etc.).
- **Robustness:** Health checks for background processes.

## Constraints
- **Read-Only:** The application must not modify the indexed project files.
- **Environment:** Runs in WSL, interacts with Windows Host.
- **Tech Stack:** Next.js, Tailwind CSS, Shadcn/UI.

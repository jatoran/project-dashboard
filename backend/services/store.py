import json
import os
import time
from pathlib import Path
from typing import List
from ..models import Project
from .scanner import ProjectScanner
from ..utils.path_utils import normalize_path, resolve_path_case

# Use absolute path relative to this file for reliable data location
DATA_FILE = Path(__file__).parent.parent / "data" / "projects.json"

class ProjectStore:
    def __init__(self):
        self.scanner = ProjectScanner()
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump([], f)

    def get_all(self, sort_by_palette_recency: bool = False) -> List[Project]:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        projects = [Project(**p) for p in data]

        if sort_by_palette_recency:
            # Sort by last_palette_open descending (most recent first)
            # Projects with no palette history go to the bottom
            projects.sort(
                key=lambda p: p.last_palette_open if p.last_palette_open else 0,
                reverse=True
            )

        return projects

    def mark_palette_open(self, project_path: str) -> None:
        """Update the last_palette_open timestamp for a project."""
        projects = self.get_all()
        for p in projects:
            if p.path == project_path:
                p.last_palette_open = time.time()
                self._save(projects)
                return
        # Project not found is fine - just ignore

    def add_project(self, path_str: str) -> Project:
        print(f"[DEBUG] add_project received path: '{path_str}'")
        
        # Normalize and resolve case for consistent paths
        normalized_path = normalize_path(path_str)
        resolved_path = resolve_path_case(normalized_path)
        print(f"[DEBUG] Resolved path: '{resolved_path}'")
            
        try:
            project = self.scanner.scan(resolved_path)
        except Exception as e:
            print(f"[ERROR] Scanner failed for path '{resolved_path}': {e}")
            raise e
        
        projects = self.get_all()
        # Check duplicates
        if any(p.path == project.path for p in projects):
            print(f"[DEBUG] Duplicate project found: {project.path}")
            raise ValueError("Project already exists")
            
        projects.append(project)
        self._save(projects)
        return project

    def remove_project(self, project_id: str):
        projects = self.get_all()
        initial_len = len(projects)
        projects = [p for p in projects if p.id != project_id]
        if len(projects) == initial_len:
            raise ValueError(f"Project with ID {project_id} not found.")
        self._save(projects)

    def refresh_project(self, project_id: str) -> Project:
        """Rescan a project to update discovered docs. Preserves user customizations."""
        projects = self.get_all()
        existing = None
        for p in projects:
            if p.id == project_id:
                existing = p
                break
        
        if not existing:
            raise ValueError(f"Project with ID {project_id} not found.")
        
        # Normalize and resolve path case
        scan_path = resolve_path_case(existing.path)
        
        # Rescan the project path
        scanned = self.scanner.scan(scan_path)
        
        # Update discovered fields from scan, preserve user customizations
        existing.name = scanned.name
        existing.type = scanned.type
        existing.tags = scanned.tags
        existing.description = scanned.description
        existing.git_status = scanned.git_status
        existing.docs = scanned.docs  # Fully replace discovered docs
        existing.vscode_workspace_file = scanned.vscode_workspace_file
        existing.frontend_url = scanned.frontend_url
        existing.backend_port = scanned.backend_port
        # Update path to normalized version
        existing.path = scanned.path
        # Keep: custom_links, custom_docs, port overrides, position
        
        self._save(projects)
        return existing

    def add_custom_link(self, project_id: str, name: str, url: str) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                if p.custom_links is None: p.custom_links = []
                p.custom_links.append({"name": name, "url": url})
                self._save(projects)
                return p
        raise ValueError("Project not found")

    def remove_custom_link(self, project_id: str, name: str) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                if p.custom_links:
                    p.custom_links = [l for l in p.custom_links if l['name'] != name]
                    self._save(projects)
                return p
        raise ValueError("Project not found")

    def add_custom_doc(self, project_id: str, name: str, path: str) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                if p.custom_docs is None: p.custom_docs = []
                p.custom_docs.append({"name": name, "path": path})
                self._save(projects)
                return p
        raise ValueError("Project not found")

    def update_ports(self, project_id: str, frontend_port: str | None, backend_port: str | None) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                p.frontend_port_override = frontend_port or None
                p.backend_port_override = backend_port or None
                self._save(projects)
                return p
        raise ValueError("Project not found")

    def remove_custom_doc(self, project_id: str, name: str) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                if p.custom_docs:
                    p.custom_docs = [d for d in p.custom_docs if d['name'] != name]
                    self._save(projects)
                return p
        raise ValueError("Project not found")

    def reorder(self, order: List[str]) -> List[Project]:
        """Update project positions based on provided order of IDs."""
        projects = self.get_all()
        id_to_project = {p.id: p for p in projects}
        
        # Update positions based on order
        for i, project_id in enumerate(order):
            if project_id in id_to_project:
                id_to_project[project_id].position = i
        
        # For any projects not in the order list, set position to end
        max_pos = len(order)
        for p in projects:
            if p.id not in order:
                p.position = max_pos
                max_pos += 1
        
        self._save(projects)
        return projects

    def _save(self, projects: List[Project]):
        with open(DATA_FILE, "w") as f:
            json.dump([p.dict() for p in projects], f, indent=2)


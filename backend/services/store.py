import json
import os
from typing import List
from backend.models import Project
from backend.services.scanner import ProjectScanner

DATA_FILE = "backend/data/projects.json"

class ProjectStore:
    def __init__(self):
        self.scanner = ProjectScanner()
        self._ensure_file()

    def _ensure_file(self):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        if not os.path.exists(DATA_FILE):
            with open(DATA_FILE, "w") as f:
                json.dump([], f)

    def get_all(self) -> List[Project]:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
        # Re-scan on load? For now, just return stored data.
        # Better: Store paths, and scan on demand or cache.
        # For Phase 1 MVP: We will store the FULL project object 
        # but maybe re-scanning is safer to keep git status fresh.
        # Let's just return what's there for speed, user can "refresh".
        return [Project(**p) for p in data]

    def add_project(self, path_str: str) -> Project:
        project = self.scanner.scan(path_str)
        
        projects = self.get_all()
        # Check duplicates
        if any(p.path == project.path for p in projects):
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

    def _save(self, projects: List[Project]):
        with open(DATA_FILE, "w") as f:
            json.dump([p.dict() for p in projects], f, indent=2)

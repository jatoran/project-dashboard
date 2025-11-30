import json
import os
from typing import List
from backend.models import Project
from backend.services.scanner import ProjectScanner
from backend.utils.path_utils import windows_to_linux, resolve_path_case

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
        return [Project(**p) for p in data]

    def add_project(self, path_str: str) -> Project:
        print(f"[DEBUG] add_project received path: '{path_str}'")
        
        # Convert potential Windows path to Linux path for scanning/storage
        linux_path_str = windows_to_linux(path_str)
        print(f"[DEBUG] converted to linux path: '{linux_path_str}'")
        
        # Resolve case sensitivity (e.g. 'Projects' vs 'projects')
        resolved_path = resolve_path_case(linux_path_str)
        if resolved_path != linux_path_str:
            print(f"[DEBUG] Resolved path case: '{linux_path_str}' -> '{resolved_path}'")
            
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

    def remove_custom_doc(self, project_id: str, name: str) -> Project:
        projects = self.get_all()
        for p in projects:
            if p.id == project_id:
                if p.custom_docs:
                    p.custom_docs = [d for d in p.custom_docs if d['name'] != name]
                    self._save(projects)
                return p
        raise ValueError("Project not found")

    def _save(self, projects: List[Project]):
        with open(DATA_FILE, "w") as f:
            json.dump([p.dict() for p in projects], f, indent=2)

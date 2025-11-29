import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict
from backend.models import Project
import uuid

class ProjectScanner:
    def scan(self, path_str: str) -> Project:
        path = Path(path_str)
        if not path.exists():
            raise ValueError(f"Path does not exist: {path_str}")

        name = path.name
        project_type = "generic"
        tags = []
        docs = []

        # Detect Type
        if (path / "package.json").exists():
            project_type = "node"
            tags.append("javascript")
            if (path / "tsconfig.json").exists():
                tags.append("typescript")
        elif (path / "requirements.txt").exists() or (path / "pyproject.toml").exists():
            project_type = "python"
            tags.append("python")
        elif (path / "Cargo.toml").exists():
            project_type = "rust"
            tags.append("rust")
        elif (path / "docker-compose.yml").exists():
            project_type = "docker"
            tags.append("docker")

        # Detect Docs
        for doc_file in ["README.md", "openapi.json", "swagger.json"]:
            if (path / doc_file).exists():
                docs.append({"name": doc_file, "path": str(path / doc_file)})

        # Basic Git Check (Simplified)
        git_status = None
        if (path / ".git").exists():
            tags.append("git")
            # Could add subprocess call to 'git status' here later
            git_status = "Clean" 

        return Project(
            id=str(uuid.uuid4()),
            name=name,
            path=str(path.absolute()),
            type=project_type,
            tags=tags,
            docs=docs,
            git_status=git_status
        )

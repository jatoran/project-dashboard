import os
import json
from pathlib import Path
from typing import List, Dict, Optional
from ..models import Project
import uuid
import re
import yaml
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Timeout for the entire scan operation (seconds)
SCAN_TIMEOUT = 10

# Max files to check in any directory listing
MAX_DIR_ENTRIES = 200

# Known subdirs to check (don't iterate unknown dirs)
KNOWN_SUBDIRS = ['frontend', 'client', 'web', 'ui', 'app', 'backend', 'server', 'api', 'src', 'docs']


def safe_listdir(path: Path, max_entries: int = MAX_DIR_ENTRIES) -> List[str]:
    """Safely list directory with a cap on entries."""
    try:
        entries = os.listdir(path)
        return entries[:max_entries]
    except (OSError, PermissionError):
        return []


def safe_read_text(path: Path, max_size: int = 100_000) -> str:
    """Safely read file text with size limit."""
    try:
        if not path.exists() or not path.is_file():
            return ""
        if path.stat().st_size > max_size:
            return ""
        return path.read_text(errors='ignore')
    except (OSError, PermissionError):
        return ""


class ProjectScanner:
    def scan(self, path_str: str) -> Project:
        """Scan a project directory with timeout protection."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._do_scan, path_str)
            try:
                return future.result(timeout=SCAN_TIMEOUT)
            except FuturesTimeoutError:
                raise ValueError(f"Scan timed out after {SCAN_TIMEOUT}s for: {path_str}")

    def _do_scan(self, path_str: str) -> Project:
        """Internal scan implementation."""
        path = Path(path_str)
        if not path.exists():
            raise ValueError(f"Path does not exist: {path_str}")

        name = path.name
        project_type = "generic"
        tags = set()
        docs = []

        # --- Phase 1: Type Detection (check known files only) ---

        # Check Node
        if (path / "package.json").exists():
            project_type = "node"
            tags.add("node")
            tags.add("javascript")

            pkg_content = safe_read_text(path / "package.json")
            if pkg_content:
                try:
                    pkg = json.loads(pkg_content)
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    if "typescript" in deps: tags.add("typescript")
                    if "react" in deps: tags.add("react")
                    if "next" in deps: tags.add("next.js")
                    if "vue" in deps: tags.add("vue")
                    if "express" in deps: tags.add("express")
                    if "@nestjs/core" in deps: tags.add("nestjs")
                    if "tailwindcss" in deps: tags.add("tailwind")
                except json.JSONDecodeError:
                    pass

            if (path / "tsconfig.json").exists():
                tags.add("typescript")

        # Check known subdirs for package.json
        for d in ['frontend', 'client', 'web', 'ui', 'app']:
            sub_pkg = path / d / "package.json"
            if sub_pkg.exists():
                tags.add("node")
                tags.add("javascript")
                pkg_content = safe_read_text(sub_pkg)
                if pkg_content:
                    try:
                        pkg = json.loads(pkg_content)
                        deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                        if "typescript" in deps: tags.add("typescript")
                        if "react" in deps: tags.add("react")
                        if "next.js" in deps or "next" in deps: tags.add("next.js")
                        if "vue" in deps: tags.add("vue")
                        if "tailwindcss" in deps: tags.add("tailwind")
                    except json.JSONDecodeError:
                        pass

        # Check Python
        python_indicators = ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"]
        is_fastapi = False
        for f in python_indicators:
            if (path / f).exists():
                project_type = "python"
                tags.add("python")
                content = safe_read_text(path / f).lower()
                if "fastapi" in content:
                    tags.add("fastapi")
                    is_fastapi = True
                if "django" in content: tags.add("django")
                if "flask" in content: tags.add("flask")
                break

        # Check backend subdir for Python
        if (path / "backend" / "requirements.txt").exists():
            tags.add("python")
            content = safe_read_text(path / "backend" / "requirements.txt").lower()
            if "fastapi" in content:
                tags.add("fastapi")
                is_fastapi = True

        # Check Rust
        if (path / "Cargo.toml").exists():
            project_type = "rust"
            tags.add("rust")
            content = safe_read_text(path / "Cargo.toml")
            if "actix" in content: tags.add("actix")
            if "tokio" in content: tags.add("tokio")
            if "axum" in content: tags.add("axum")

        # Check Docker
        has_docker = False
        if (path / "docker-compose.yml").exists() or (path / "Dockerfile").exists():
            has_docker = True
            tags.add("docker")
            if project_type == "generic":
                project_type = "docker"

        # Check other languages (quick file existence checks only)
        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            tags.add("java")
            if project_type == "generic": project_type = "java"

        if (path / "go.mod").exists():
            tags.add("go")
            if project_type == "generic": project_type = "go"

        if (path / "Gemfile").exists():
            tags.add("ruby")
            if project_type == "generic": project_type = "ruby"

        # Check Git
        git_status = None
        if (path / ".git").exists():
            tags.add("git")
            git_status = "Clean"

        # --- Phase 2: Docs (root markdown only + docs/ folder limited) ---
        root_files = safe_listdir(path)
        for f in root_files:
            if f.lower().endswith('.md'):
                docs.append({"name": f, "path": str(path / f), "type": "markdown"})

        # Scan docs/ folder (1 level only)
        docs_path = path / "docs"
        if docs_path.exists() and docs_path.is_dir():
            docs_files = safe_listdir(docs_path)
            for f in docs_files:
                fp = docs_path / f
                if f.lower().endswith('.md') and fp.is_file():
                    docs.append({"name": f, "path": str(fp), "type": "markdown"})

        # Check for API definitions
        for doc_file in ["openapi.json", "swagger.json"]:
            if (path / doc_file).exists():
                doc_type = "openapi" if doc_file == "openapi.json" else "swagger"
                docs.append({"name": doc_file, "path": str(path / doc_file), "type": doc_type})

        # --- Phase 3: Port Detection (minimal scanning) ---
        detected_port = None

        # Check docker-compose for ports
        if (path / "docker-compose.yml").exists():
            content = safe_read_text(path / "docker-compose.yml")
            if content:
                try:
                    data = yaml.safe_load(content)
                    services = data.get('services', {}) if data else {}

                    for key in ['backend', 'api', 'server', 'app', 'web']:
                        if key in services:
                            svc = services[key]
                            if 'ports' in svc:
                                for p in svc['ports']:
                                    p_str = str(p)
                                    if ':' in p_str:
                                        detected_port = p_str.split(':')[0]
                                        break
                            break
                except yaml.YAMLError:
                    pass

        # Check README for port mentions
        if not detected_port:
            for md_file in ['README.md', 'readme.md']:
                if (path / md_file).exists():
                    content = safe_read_text(path / md_file)
                    match = re.search(r"localhost:(\d{4,5})/docs", content, re.IGNORECASE)
                    if match:
                        detected_port = match.group(1)
                        break

        # Generate API docs links if FastAPI detected
        if is_fastapi or detected_port:
            final_port = detected_port if detected_port else "8000"
            if is_fastapi or (detected_port and "80" in detected_port):
                docs.append({"name": "Swagger UI", "path": f"http://localhost:{final_port}/docs", "type": "link"})
                docs.append({"name": "ReDoc", "path": f"http://localhost:{final_port}/redoc", "type": "link"})
                docs.append({"name": "OpenAPI JSON", "path": f"http://localhost:{final_port}/openapi.json", "type": "link"})

        # --- Phase 4: Frontend URL Detection ---
        frontend_url = None

        # Check vite config
        for cfg in ["vite.config.ts", "vite.config.js"]:
            if (path / cfg).exists():
                content = safe_read_text(path / cfg)
                match = re.search(r"port:\s*(\d{4})", content)
                if match:
                    frontend_url = f"http://localhost:{match.group(1)}"
                    break

        # Check package.json scripts for port
        if not frontend_url:
            for pkg_loc in [path, path / "frontend", path / "client"]:
                pkg_path = pkg_loc / "package.json"
                if pkg_path.exists():
                    content = safe_read_text(pkg_path)
                    if content:
                        try:
                            pkg = json.loads(content)
                            scripts = pkg.get("scripts", {})
                            for script_cmd in scripts.values():
                                port_match = re.search(r"(?:-p|--port)[=\s]+(\d{4,5})", str(script_cmd))
                                if not port_match:
                                    port_match = re.search(r"PORT=(\d{4,5})", str(script_cmd))
                                if port_match:
                                    frontend_url = f"http://localhost:{port_match.group(1)}"
                                    break
                        except json.JSONDecodeError:
                            pass
                if frontend_url:
                    break

        # Default frontend ports based on framework
        if not frontend_url and ("node" in tags or "javascript" in tags):
            if "next.js" in tags:
                frontend_url = "http://localhost:3000"
            elif "react" in tags:
                frontend_url = "http://localhost:3000"
            elif "vue" in tags:
                frontend_url = "http://localhost:5173"

        # --- Phase 5: VS Code Workspace ---
        vscode_workspace_file = None
        for item in root_files:
            if item.endswith(".code-workspace"):
                fp = path / item
                if fp.is_file():
                    vscode_workspace_file = str(fp)
                    break

        return Project(
            id=str(uuid.uuid4()),
            name=name,
            path=str(path.absolute()),
            type=project_type,
            tags=list(tags),
            docs=docs,
            git_status=git_status,
            vscode_workspace_file=vscode_workspace_file,
            frontend_url=frontend_url,
            backend_port=detected_port
        )

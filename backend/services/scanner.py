import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from backend.models import Project
import uuid
import re
import yaml

class ProjectScanner:
    def scan(self, path_str: str) -> Project:
        path = Path(path_str)
        if not path.exists():
            raise ValueError(f"Path does not exist: {path_str}")

        name = path.name
        project_type = "generic"
        tags = set() # Use set to avoid dupes
        docs = []

        # --- Phase 1: Tagging & Type Detection ---
        # Check Node
        if (path / "package.json").exists():
            project_type = "node" # Default to node if present
            tags.add("node")
            tags.add("javascript")
            
            try:
                pkg = json.loads((path / "package.json").read_text(errors='ignore'))
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                
                if "typescript" in deps: tags.add("typescript")
                if "react" in deps: tags.add("react")
                if "next" in deps: tags.add("next.js")
                if "vue" in deps: tags.add("vue")
                if "express" in deps: tags.add("express")
                if "@nestjs/core" in deps: tags.add("nestjs")
                if "tailwindcss" in deps: tags.add("tailwind")
            except: pass

            if (path / "tsconfig.json").exists():
                tags.add("typescript")
        
        # Check Python
        has_python = False
        python_indicators = ["requirements.txt", "pyproject.toml", "Pipfile", "setup.py"]
        if any((path / f).exists() for f in python_indicators):
            project_type = "python" # Override if explicit python
            tags.add("python")
            has_python = True
            
            # Scan for frameworks
            content = ""
            for f in python_indicators:
                if (path / f).exists():
                    content += (path / f).read_text(errors='ignore').lower()
            
            if "fastapi" in content: tags.add("fastapi")
            if "django" in content: tags.add("django")
            if "flask" in content: tags.add("flask")
            if "pandas" in content: tags.add("pandas")
            if "torch" in content: tags.add("pytorch")

        else:
            # Check common subdirs like 'backend'
            if (path / "backend" / "requirements.txt").exists():
                tags.add("python")
                has_python = True

        # Check Rust
        if (path / "Cargo.toml").exists():
            project_type = "rust"
            tags.add("rust")
            try:
                content = (path / "Cargo.toml").read_text(errors='ignore')
                if "actix" in content: tags.add("actix")
                if "tokio" in content: tags.add("tokio")
                if "axum" in content: tags.add("axum")
            except: pass

        # Check Docker
        has_docker = False
        if (path / "docker-compose.yml").exists() or (path / "Dockerfile").exists():
            has_docker = True
            tags.add("docker")
            # If purely docker at root, set type to docker
            if project_type == "generic":
                project_type = "docker"

        # Check Git
        git_status = None
        if (path / ".git").exists():
            tags.add("git")
            git_status = "Clean"

        # --- Phase 2: Static File Docs ---
        # Scan for Markdown files in root
        try:
            for f in os.listdir(path):
                if f.lower().endswith('.md'):
                    docs.append({"name": f, "path": str(path / f), "type": "markdown"})
        except: pass

        # Scan for Markdown files in docs/ (recursive)
        docs_path = path / "docs"
        if docs_path.exists():
            for root, _, files in os.walk(str(docs_path)):
                for f in files:
                    if f.lower().endswith('.md'):
                        # Create a display name relative to docs/ folder
                        rel_dir = os.path.relpath(root, str(docs_path))
                        if rel_dir == ".":
                            disp_name = f
                        else:
                            disp_name = f"{rel_dir}/{f}".replace("\\", "/")
                        
                        docs.append({
                            "name": disp_name, 
                            "path": str(Path(root) / f), 
                            "type": "markdown"
                        })

        # Scan for API definitions
        for doc_file in ["openapi.json", "swagger.json"]:
            if (path / doc_file).exists():
                doc_type = "openapi" if doc_file == "openapi.json" else "swagger"
                docs.append({"name": doc_file, "path": str(path / doc_file), "type": doc_type})

        # --- Phase 3: API Port Detection & Dynamic Docs ---
        # We attempt to find a port if:
        # 1. It's a Python project (FastAPI potential)
        # 2. It's a Docker project (Exposed ports)
        # 3. It's a Node project (Express/NestJS potential)
        
        detected_port = None
        is_fastapi = False

        # 3a. Check for FastAPI signature anywhere
        # Scan root and immediate subdirs for requirements.txt mentioning fastapi
        search_paths = [path] + [p for p in path.iterdir() if p.is_dir() and p.name not in ['node_modules', '.git', '.venv', 'venv']]
        
        for search_path in search_paths:
            req_file = search_path / "requirements.txt"
            toml_file = search_path / "pyproject.toml"
            
            content = ""
            if req_file.exists(): content += req_file.read_text(errors='ignore').lower()
            if toml_file.exists(): content += toml_file.read_text(errors='ignore').lower()
            
            if "fastapi" in content:
                is_fastapi = True
                tags.add("fastapi")
                break

        # 3b. Strategy: Docker Compose (Best for Ports)
        if not detected_port and (path / "docker-compose.yml").exists():
            try:
                content = (path / "docker-compose.yml").read_text(errors='ignore')
                data = yaml.safe_load(content)
                services = data.get('services', {})
                
                # Heuristic: Find "backend" service or any service exposing ports
                target_svc = None
                
                # 1. Look for named services
                for key in ['backend', 'api', 'server', 'app', 'web']:
                    if key in services:
                        target_svc = services[key]
                        break
                
                # 2. If checking specifically for FastAPI/Python, prioritize that
                if not target_svc and is_fastapi:
                     # Try to find service building from Dockerfile.backend
                     for _, svc in services.items():
                         if 'build' in svc:
                             build = svc['build']
                             if isinstance(build, dict) and 'dockerfile' in build:
                                 if 'backend' in build['dockerfile'].lower():
                                     target_svc = svc
                                     break

                # Extract Port
                if target_svc and 'ports' in target_svc:
                    for p in target_svc['ports']:
                        # "8001:8001" or "8001"
                        p_str = str(p)
                        if ':' in p_str:
                            host = p_str.split(':')[0]
                            detected_port = host
                            break
                        elif p_str.isdigit():
                            detected_port = p_str
                            break
            except: pass

        # 3c. Strategy: Markdown Scanning (Contextual)
        if not detected_port:
            md_files = [f for f in os.listdir(path) if f.endswith('.md')]
            for md_file in md_files:
                try:
                    content = (path / md_file).read_text(errors='ignore')
                    # Look for "Backend ... localhost:XXXX"
                    patterns = [
                        r"(?:backend|api|server|fastapi).*?localhost:(\d{4,5})",
                        r"localhost:(\d{4,5}).*?(?:backend|api|server|fastapi|docs|swagger)",
                        r"localhost:(\d{4,5})/docs"
                    ]
                    for pat in patterns:
                        match = re.search(pat, content, re.IGNORECASE | re.DOTALL)
                        if match:
                            detected_port = match.group(1)
                            # Ignore common frontend ports unless explicit
                            if detected_port in ['3000', '4200', '5173']:
                                detected_port = None 
                                continue
                            break
                    if detected_port: break
                except: pass

        # 3d. Strategy: Frontend Configs (API_URL)
        if not detected_port:
             for root, _, files in os.walk(str(path)):
                if 'node_modules' in root or '.git' in root: continue
                for file in files:
                    if file in ['.env', '.env.local', 'constants.ts', 'config.js']:
                        try:
                            content = (Path(root) / file).read_text(errors='ignore')
                            match = re.search(r"(?:API|BACKEND|SERVER).*?localhost:(\d{4,5})", content, re.IGNORECASE)
                            if match:
                                detected_port = match.group(1)
                                break
                        except: pass
                if detected_port: break

        # --- Phase 4: Generate Links ---
        # If we confirmed FastAPI OR we found a likely backend port, generate links
        if is_fastapi or detected_port:
            final_port = detected_port if detected_port else "8000"
            
            # Only add these if we suspect it's a swagger-enabled API (FastAPI strongly implies this)
            # Or if the port was found via "API" context
            if is_fastapi or (detected_port and "80" in detected_port): # 8000, 8080, 8001
                docs.append({"name": "Swagger UI", "path": f"http://localhost:{final_port}/docs", "type": "link"})
                docs.append({"name": "ReDoc", "path": f"http://localhost:{final_port}/redoc", "type": "link"})
                docs.append({"name": "OpenAPI JSON", "path": f"http://localhost:{final_port}/openapi.json", "type": "link"})

        # --- Phase 5: VS Code Workspace ---
        vscode_workspace_file = None
        for item in os.listdir(path):
            if item.endswith(".code-workspace") and (path / item).is_file():
                vscode_workspace_file = str(path / item)
                break

        return Project(
            id=str(uuid.uuid4()),
            name=name,
            path=str(path.absolute()),
            type=project_type,
            tags=list(tags),
            docs=docs,
            git_status=git_status,
            vscode_workspace_file=vscode_workspace_file
        )
import os
import json
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from ..models import Project
import uuid
import re
import yaml

# Directories to skip during scanning (massive performance improvement)
SKIP_DIRS = {
    'node_modules', '.git', '.venv', 'venv', '__pycache__', '.tox', 
    '.pytest_cache', '.mypy_cache', 'dist', 'build', '.next', '.nuxt',
    'target', 'vendor', '.cargo', 'coverage', '.coverage', 'htmlcov',
    '.eggs', '*.egg-info', '.cache', '.parcel-cache', '.turbo',
}

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
        
        # 1a. Check Root Node
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

        # 1b. Check Subdirectory Node (frontend/client/web/ui/app)
        # If root didn't give us much, or even if it did, we scan subdirs for frontend frameworks
        potential_subdirs = ['frontend', 'client', 'web', 'ui', 'app']
        for d in potential_subdirs:
            sub_pkg = path / d / "package.json"
            if sub_pkg.exists():
                tags.add("node") # It implies node usage
                tags.add("javascript")
                try:
                    pkg = json.loads(sub_pkg.read_text(errors='ignore'))
                    deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                    
                    if "typescript" in deps: tags.add("typescript")
                    if "react" in deps: tags.add("react")
                    if "next" in deps: tags.add("next.js")
                    if "vue" in deps: tags.add("vue")
                    if "tailwindcss" in deps: tags.add("tailwind")
                except: pass
        
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
        
        # --- Phase 1.5: Static Web & Basic File Detection (Fallback) ---
        # If still generic (or generic-ish), check for raw source files
        
        # HTML/CSS/JS (Static Site)
        has_html = False
        if (path / "index.html").exists() or (path / "public" / "index.html").exists():
            has_html = True
            tags.add("html")
            if project_type == "generic":
                project_type = "static-web"
        
        # Check for CSS
        # Scan root and common assets dirs
        css_found = False
        for d in ['.', 'styles', 'css', 'public', 'assets', 'src']:
            if not (path / d).exists(): continue
            if any(f.endswith('.css') for f in os.listdir(path / d) if os.path.isfile(path / d / f)):
                css_found = True
                break
        if css_found:
            tags.add("css")
            
        # Check for JS (if not already Node)
        if "javascript" not in tags:
             js_found = False
             for d in ['.', 'scripts', 'js', 'public', 'assets', 'src']:
                if not (path / d).exists(): continue
                if any(f.endswith('.js') for f in os.listdir(path / d) if os.path.isfile(path / d / f)):
                    js_found = True
                    break
             if js_found:
                 tags.add("javascript")
                 if project_type == "generic" and has_html:
                      project_type = "static-web"

        # Basic Language Detection for others
        if (path / "pom.xml").exists() or (path / "build.gradle").exists():
            tags.add("java")
            if project_type == "generic": project_type = "java"

        if (path / "go.mod").exists() or any(f.endswith('.go') for f in os.listdir(path) if os.path.isfile(path/f)):
             tags.add("go")
             if project_type == "generic": project_type = "go"
             
        if (path / "Gemfile").exists() or any(f.endswith('.rb') for f in os.listdir(path) if os.path.isfile(path/f)):
             tags.add("ruby")
             if project_type == "generic": project_type = "ruby"

        if any(f.endswith('.php') for f in os.listdir(path) if os.path.isfile(path/f)):
             tags.add("php")
             if project_type == "generic": project_type = "php"

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

        # 3d. Strategy: Frontend Configs (API_URL) - Limited depth search
        if not detected_port:
            # Only scan first 2 levels deep to avoid traversing huge directories
            for root, dirs, files in os.walk(str(path)):
                # Prune directories in-place (prevents os.walk from entering them)
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                
                # Limit depth to 2 levels
                depth = root.replace(str(path), '').count(os.sep)
                if depth >= 2:
                    dirs.clear()
                    continue
                
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

        # --- Phase 5: Frontend URL Detection ---
        frontend_url = None
        
        # 5a. Check Vite Config (Common in React/Vue)
        if not frontend_url:
             for cfg in ["vite.config.ts", "vite.config.js"]:
                 if (path / cfg).exists():
                     try:
                         content = (path / cfg).read_text(errors='ignore')
                         # Look for port: XXXX in server config
                         match = re.search(r"port:\s*(\d{4})", content)
                         if match:
                             frontend_url = f"http://localhost:{match.group(1)}"
                             break
                     except: pass

        # 5b. Check Node scripts (Root + Subdirectories)
        if not frontend_url:
            files_to_check = [path / "package.json"]
            for d in ['frontend', 'client', 'web', 'ui', 'app']:
                files_to_check.append(path / d / "package.json")

            detected_fe_port = None
            
            for pkg_path in files_to_check:
                if pkg_path.exists():
                    try:
                        pkg = json.loads(pkg_path.read_text(errors='ignore'))
                        scripts = pkg.get("scripts", {})
                        for script_cmd in scripts.values():
                            # Look for -p XXXX, --port XXXX, -p=XXXX, --port=XXXX, PORT=XXXX
                            port_match = re.search(r"(?:-p|--port)[=\s]+(\d{4,5})", script_cmd)
                            if not port_match:
                                port_match = re.search(r"PORT=(\d{4,5})", script_cmd)
                            
                            if port_match:
                                detected_fe_port = port_match.group(1)
                                break
                    except: pass
                if detected_fe_port: break

            if not detected_fe_port and (project_type == "node" or "node" in tags or "javascript" in tags):
                # Default based on framework tags
                if "next.js" in tags: detected_fe_port = "3000"
                elif "react" in tags: detected_fe_port = "3000" # CRA default
                elif "vite" in tags or "vue" in tags: detected_fe_port = "5173"
                elif "angular" in tags: detected_fe_port = "4200"
            
            if detected_fe_port:
                frontend_url = f"http://localhost:{detected_fe_port}"
        
        # 5c. Check Docker Compose (Most reliable for high ports)
        if has_docker and (path / "docker-compose.yml").exists():
             try:
                content = (path / "docker-compose.yml").read_text(errors='ignore')
                data = yaml.safe_load(content)
                services = data.get('services', {})
                
                # Priority 1: Explicit service name match
                target_svc = None
                for key in services.keys():
                    if key.lower() in ['frontend', 'client', 'ui', 'web', 'app']:
                         target_svc = services[key]
                         break
                
                if target_svc and 'ports' in target_svc:
                    for p in target_svc['ports']:
                        p_str = str(p)
                        if ':' in p_str:
                            host_port = p_str.split(':')[0]
                            # Valid range check (avoid MySQL 3306, Postgres 5432, Redis 6379)
                            if host_port.isdigit():
                                port_num = int(host_port)
                                if port_num > 1024 and port_num not in [3306, 5432, 6379, 8080, 8000, 27017]:
                                     frontend_url = f"http://localhost:{port_num}"
                                     break
             except: pass

        # 5d. Check Markdown Documentation (Contextual fallback)
        if not frontend_url:
            md_files = [f for f in os.listdir(path) if f.endswith('.md')]
            for md_file in md_files:
                try:
                    content = (path / md_file).read_text(errors='ignore')
                    # Look for "Frontend: http://localhost:XXXX"
                    patterns = [
                        r"(?:frontend|client|ui).*?http://localhost:(\d{4,5})",
                        r"http://localhost:(\d{4,5}).*?(?:frontend|client|ui)",
                        r"Access Frontend: `?http://localhost:(\d{4,5})`?",
                        r"(?:Frontend|UI|Client)\s+\(Port\s+(\d{4,5})\)" # New pattern for "Frontend (Port XXXX)"
                    ]
                    for pat in patterns:
                        match = re.search(pat, content, re.IGNORECASE | re.DOTALL)
                        if match:
                            frontend_url = f"http://localhost:{match.group(1)}"
                            break
                    if frontend_url: break
                except: pass

        # --- Phase 6: VS Code Workspace ---
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
            vscode_workspace_file=vscode_workspace_file,
            frontend_url=frontend_url,
            backend_port=detected_port
        )

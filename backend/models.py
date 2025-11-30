from pydantic import BaseModel
from typing import List, Optional, Dict

class Project(BaseModel):
    id: str
    name: str
    path: str
    type: str  # 'node', 'python', 'rust', 'docker', 'generic'
    tags: List[str]
    description: Optional[str] = None
    git_status: Optional[str] = None
    docs: List[Dict[str, str]] = [] # [{'name': 'Swagger', 'path': 'http://...', 'type': 'link'}]
    custom_links: List[Dict[str, str]] = [] # [{'name': 'My Link', 'url': 'http://...'}]
    custom_docs: List[Dict[str, str]] = [] # [{'name': 'Notes', 'path': '/path/to/notes.md'}]
    vscode_workspace_file: Optional[str] = None
    frontend_url: Optional[str] = None
    backend_port: Optional[str] = None
    frontend_port_override: Optional[str] = None
    backend_port_override: Optional[str] = None

class CreateProjectRequest(BaseModel):
    path: str

class LaunchRequest(BaseModel):
    project_path: str
    launch_type: str # 'vscode', 'explorer', 'terminal'

class AddLinkRequest(BaseModel):
    name: str
    url: str

class AddDocRequest(BaseModel):
    name: str
    path: str

class PortOverrideRequest(BaseModel):
    frontend_port: Optional[str] = None
    backend_port: Optional[str] = None

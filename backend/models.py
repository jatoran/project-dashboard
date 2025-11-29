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
    docs: List[Dict[str, str]] = [] # [{'name': 'README', 'path': '...', 'type': 'file' | 'openapi' | 'swagger'}]
    vscode_workspace_file: Optional[str] = None

class CreateProjectRequest(BaseModel):
    path: str

class LaunchRequest(BaseModel):
    project_path: str
    launch_type: str # 'vscode', 'explorer', 'terminal'

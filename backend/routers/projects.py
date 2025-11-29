from fastapi import APIRouter, HTTPException
from typing import List
import os
from backend.models import Project, CreateProjectRequest, LaunchRequest
from backend.services.store import ProjectStore
from backend.services.launcher import Launcher

router = APIRouter()
store = ProjectStore()
launcher = Launcher()

@router.get("/projects", response_model=List[Project])
def get_projects():
    return store.get_all()

@router.get("/files/content")
def get_file_content(path: str):
    """Reads and returns the content of a file."""
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Basic security: ensure it's a file
    if not os.path.isfile(path):
        raise HTTPException(status_code=400, detail="Path is not a file")
        
    # Try reading
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.post("/projects", response_model=Project)
def add_project(request: CreateProjectRequest):
    try:
        return store.add_project(request.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    try:
        store.remove_project(project_id)
        return {"status": "success", "message": f"Project {project_id} removed"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/launch")
def launch_project(request: LaunchRequest):
    try:
        launcher.launch(request.project_path, request.launch_type)
        return {"status": "success", "message": f"Launched {request.launch_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

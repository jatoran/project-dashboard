from fastapi import APIRouter, HTTPException
from typing import List
from backend.models import Project, CreateProjectRequest, LaunchRequest
from backend.services.store import ProjectStore
from backend.services.launcher import Launcher

router = APIRouter()
store = ProjectStore()
launcher = Launcher()

@router.get("/projects", response_model=List[Project])
def get_projects():
    return store.get_all()

@router.post("/projects", response_model=Project)
def add_project(request: CreateProjectRequest):
    try:
        return store.add_project(request.path)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/launch")
def launch_project(request: LaunchRequest):
    try:
        launcher.launch(request.project_path, request.launch_type)
        return {"status": "success", "message": f"Launched {request.launch_type}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import rate_limit
from app.modules.auth.router import get_current_user
from app.modules.auth.models import User
from app.modules.devtools import service
from app.modules.devtools.schemas import (
    ProjectCreate, ProjectUpdate, ProjectOut, ProjectStatusUpdate, ProjectDashboard,
    TaskCreate, TaskOut, TaskStatusUpdate,
    CodeSnippetCreate, CodeSnippetOut,
    ApiEndpointCreate, ApiEndpointOut,
)

router = APIRouter(prefix="/devtools", tags=["Développement logiciel"])


# --- Projets ---

@router.post(
    "/projects",
    response_model=ProjectOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=20, window_seconds=60))],
)
def create_project(
    data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.create_project(db, current_user.id, data)


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_projects(db, current_user.id)


@router.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: str,
    data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_project(db, project_id, current_user.id, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/projects/{project_id}/status", response_model=ProjectOut)
def update_project_status(
    project_id: str,
    data: ProjectStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_project_status(db, project_id, current_user.id, data.status)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_project(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/projects/{project_id}/dashboard", response_model=ProjectDashboard)
def get_project_dashboard(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_project_dashboard(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Tâches ---

@router.post(
    "/projects/{project_id}/tasks",
    response_model=TaskOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=40, window_seconds=60))],
)
def add_task(
    project_id: str,
    data: TaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_task(db, project_id, current_user.id, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: str,
    status_filter: str | None = Query(None, alias="status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_tasks(db, project_id, current_user.id, status_filter=status_filter)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.patch("/tasks/{task_id}/status", response_model=TaskOut)
def update_task_status(
    task_id: str,
    data: TaskStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.update_task_status(db, task_id, current_user.id, data.status)
    except service.TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_task(db, task_id, current_user.id)
    except service.TaskNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Bibliothèque de snippets ---

@router.post(
    "/snippets",
    response_model=CodeSnippetOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def create_snippet(
    data: CodeSnippetCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.create_snippet(db, current_user.id, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.get("/snippets", response_model=list[CodeSnippetOut])
def list_snippets(
    language: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return service.list_snippets(db, current_user.id, language=language)


@router.get("/snippets/{snippet_id}", response_model=CodeSnippetOut)
def get_snippet(
    snippet_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.get_snippet(db, snippet_id, current_user.id)
    except service.SnippetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/snippets/{snippet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_snippet(
    snippet_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_snippet(db, snippet_id, current_user.id)
    except service.SnippetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# --- Documentation d'API ---

@router.post(
    "/projects/{project_id}/api-endpoints",
    response_model=ApiEndpointOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))],
)
def add_api_endpoint(
    project_id: str,
    data: ApiEndpointCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.add_api_endpoint(db, project_id, current_user.id, data)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.DuplicateEndpointError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/projects/{project_id}/api-endpoints", response_model=list[ApiEndpointOut])
def list_api_endpoints(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return service.list_api_endpoints(db, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


@router.delete("/projects/{project_id}/api-endpoints/{endpoint_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_endpoint(
    project_id: str,
    endpoint_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        service.delete_api_endpoint(db, endpoint_id, project_id, current_user.id)
    except service.ProjectNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except service.EndpointNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

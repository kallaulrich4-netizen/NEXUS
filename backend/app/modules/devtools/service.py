from collections import defaultdict
from datetime import date

from sqlalchemy.orm import Session

from app.modules.devtools.models import Project, Task, CodeSnippet, ApiEndpointDoc


class ProjectNotFoundError(Exception):
    """Levée quand un projet n'existe pas ou n'appartient pas à l'utilisateur."""


class TaskNotFoundError(Exception):
    """Levée quand une tâche n'existe pas ou n'appartient pas à un projet de l'utilisateur."""


class SnippetNotFoundError(Exception):
    """Levée quand un snippet n'existe pas ou n'appartient pas à l'utilisateur."""


class DuplicateEndpointError(Exception):
    """Levée quand un endpoint (méthode + chemin) est déjà documenté pour ce projet."""


class EndpointNotFoundError(Exception):
    """Levée quand un endpoint documenté n'existe pas pour ce projet."""


# --- Projets ---

def create_project(db: Session, owner_id: str, data) -> Project:
    project = Project(owner_id=owner_id, status="planification", **data.model_dump())
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str, owner_id: str) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.owner_id == owner_id).first()
    if project is None:
        raise ProjectNotFoundError("Projet introuvable.")
    return project


def list_projects(db: Session, owner_id: str) -> list[Project]:
    return db.query(Project).filter(Project.owner_id == owner_id).order_by(Project.updated_at.desc()).all()


def update_project(db: Session, project_id: str, owner_id: str, data) -> Project:
    project = get_project(db, project_id, owner_id)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    db.commit()
    db.refresh(project)
    return project


def update_project_status(db: Session, project_id: str, owner_id: str, new_status: str) -> Project:
    project = get_project(db, project_id, owner_id)
    project.status = new_status
    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: str, owner_id: str) -> None:
    project = get_project(db, project_id, owner_id)
    db.delete(project)
    db.commit()


def get_project_dashboard(db: Session, project_id: str, owner_id: str) -> dict:
    project = get_project(db, project_id, owner_id)
    tasks = db.query(Task).filter(Task.project_id == project_id).all()

    tasks_by_status: dict[str, int] = defaultdict(int)
    overdue_count = 0
    today = date.today()
    for task in tasks:
        tasks_by_status[task.status] += 1
        if task.due_date and task.due_date < today and task.status != "termine":
            overdue_count += 1

    return {
        "project_id": project.id,
        "project_name": project.name,
        "total_tasks": len(tasks),
        "tasks_by_status": dict(tasks_by_status),
        "overdue_tasks_count": overdue_count,
    }


# --- Tâches ---

def add_task(db: Session, project_id: str, owner_id: str, data) -> Task:
    get_project(db, project_id, owner_id)
    task = Task(project_id=project_id, status="a_faire", **data.model_dump())
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def list_tasks(db: Session, project_id: str, owner_id: str, status_filter: str | None = None) -> list[Task]:
    get_project(db, project_id, owner_id)
    q = db.query(Task).filter(Task.project_id == project_id)
    if status_filter:
        q = q.filter(Task.status == status_filter)
    return q.order_by(Task.created_at.desc()).all()


def _get_task_for_owner(db: Session, task_id: str, owner_id: str) -> Task:
    task = (
        db.query(Task)
        .join(Project)
        .filter(Task.id == task_id, Project.owner_id == owner_id)
        .first()
    )
    if task is None:
        raise TaskNotFoundError("Tâche introuvable.")
    return task


def update_task_status(db: Session, task_id: str, owner_id: str, new_status: str) -> Task:
    task = _get_task_for_owner(db, task_id, owner_id)
    task.status = new_status
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: Session, task_id: str, owner_id: str) -> None:
    task = _get_task_for_owner(db, task_id, owner_id)
    db.delete(task)
    db.commit()


# --- Bibliothèque de snippets ---

def create_snippet(db: Session, owner_id: str, data) -> CodeSnippet:
    if data.project_id:
        get_project(db, data.project_id, owner_id)  # vérifie l'appartenance si rattaché à un projet
    snippet = CodeSnippet(owner_id=owner_id, **data.model_dump())
    db.add(snippet)
    db.commit()
    db.refresh(snippet)
    return snippet


def list_snippets(db: Session, owner_id: str, language: str | None = None) -> list[CodeSnippet]:
    q = db.query(CodeSnippet).filter(CodeSnippet.owner_id == owner_id)
    if language:
        q = q.filter(CodeSnippet.language == language.lower())
    return q.order_by(CodeSnippet.created_at.desc()).all()


def get_snippet(db: Session, snippet_id: str, owner_id: str) -> CodeSnippet:
    snippet = db.query(CodeSnippet).filter(CodeSnippet.id == snippet_id, CodeSnippet.owner_id == owner_id).first()
    if snippet is None:
        raise SnippetNotFoundError("Snippet introuvable.")
    return snippet


def delete_snippet(db: Session, snippet_id: str, owner_id: str) -> None:
    snippet = get_snippet(db, snippet_id, owner_id)
    db.delete(snippet)
    db.commit()


# --- Documentation d'API ---

def add_api_endpoint(db: Session, project_id: str, owner_id: str, data) -> ApiEndpointDoc:
    get_project(db, project_id, owner_id)

    existing = (
        db.query(ApiEndpointDoc)
        .filter(
            ApiEndpointDoc.project_id == project_id,
            ApiEndpointDoc.method == data.method,
            ApiEndpointDoc.path == data.path,
        )
        .first()
    )
    if existing is not None:
        raise DuplicateEndpointError(
            f"L'endpoint {data.method} {data.path} est déjà documenté pour ce projet."
        )

    endpoint = ApiEndpointDoc(project_id=project_id, **data.model_dump())
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


def list_api_endpoints(db: Session, project_id: str, owner_id: str) -> list[ApiEndpointDoc]:
    get_project(db, project_id, owner_id)
    return (
        db.query(ApiEndpointDoc)
        .filter(ApiEndpointDoc.project_id == project_id)
        .order_by(ApiEndpointDoc.path, ApiEndpointDoc.method)
        .all()
    )


def delete_api_endpoint(db: Session, endpoint_id: str, project_id: str, owner_id: str) -> None:
    get_project(db, project_id, owner_id)
    endpoint = (
        db.query(ApiEndpointDoc)
        .filter(ApiEndpointDoc.id == endpoint_id, ApiEndpointDoc.project_id == project_id)
        .first()
    )
    if endpoint is None:
        raise EndpointNotFoundError("Endpoint introuvable pour ce projet.")
    db.delete(endpoint)
    db.commit()

"""Task system endpoints (Section 38) + manual execution for testing/control."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.events import EventType
from app.db.session import get_db
from app.models.agent import Agent
from app.models.channel import Channel
from app.models.organization import User
from app.models.task import Task, TaskDependency
from app.services.event_bus import publish
from app.services.orchestrator import Orchestrator
from app.services.task_runner import find_ready_task_ids

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""
    agent_key: str | None = None
    channel_slug: str | None = None
    priority: str = "medium"
    input: dict = Field(default_factory=dict)
    depends_on: list[int] = Field(default_factory=list)
    max_retries: int = 2


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    assigned_agent_id: int | None
    channel_id: int | None
    priority: str
    status: str
    input: dict
    output: dict
    error: str | None
    retry_count: int
    depends_on: list[int]
    created_at: str

    model_config = {"from_attributes": True}


def _to_out(db: Session, task: Task) -> TaskOut:
    deps = [d.depends_on_id for d in db.query(TaskDependency).filter_by(task_id=task.id).all()]
    return TaskOut(id=task.id, title=task.title, description=task.description,
                   assigned_agent_id=task.assigned_agent_id, channel_id=task.channel_id,
                   priority=task.priority, status=task.status, input=task.input or {},
                   output=task.output or {}, error=task.error, retry_count=task.retry_count,
                   depends_on=deps, created_at=task.created_at.isoformat())


def _agent_by_key(db: Session, org_id: int, key: str) -> Agent | None:
    return db.query(Agent).filter(Agent.org_id == org_id, Agent.key == key).first()


@router.get("", response_model=list[TaskOut])
def list_tasks(status: str | None = None, limit: int = 50, user: User = Depends(get_current_user),
               db: Session = Depends(get_db)):
    q = db.query(Task).filter(Task.org_id == user.org_id)
    if status:
        q = q.filter(Task.status == status)
    tasks = q.order_by(Task.id.desc()).limit(min(limit, 200)).all()
    return [_to_out(db, t) for t in tasks]


@router.post("", response_model=TaskOut, status_code=201)
def create_task(data: TaskIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    agent = None
    if data.agent_key:
        agent = _agent_by_key(db, user.org_id, data.agent_key)
        if agent is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Agent '{data.agent_key}' not found")
    channel_id = None
    if data.channel_slug:
        channel = db.query(Channel).filter(Channel.org_id == user.org_id,
                                           Channel.slug == data.channel_slug).first()
        if channel is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Channel '{data.channel_slug}' not found")
        channel_id = channel.id

    task = Task(org_id=user.org_id, title=data.title, description=data.description,
                created_by_user_id=user.id, assigned_agent_id=agent.id if agent else None,
                channel_id=channel_id, priority=data.priority, input=data.input,
                max_retries=data.max_retries)
    db.add(task)
    db.flush()
    for dep_id in data.depends_on:
        dep = db.get(Task, dep_id)
        if dep is None or dep.org_id != user.org_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Dependency {dep_id} not found")
        db.add(TaskDependency(task_id=task.id, depends_on_id=dep_id))
    db.commit()
    publish(db, EventType.TASK_CREATED, {"title": task.title}, org_id=user.org_id,
            task_id=task.id, agent_id=agent.id if agent else None, commit=True)
    return _to_out(db, task)


@router.get("/ready", response_model=list[int])
def ready_tasks(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    ids = find_ready_task_ids(db)
    tasks = db.query(Task).filter(Task.org_id == user.org_id, Task.id.in_(ids or [0])).all()
    return [t.id for t in tasks]


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or task.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    return _to_out(db, task)


@router.post("/{task_id}/run", response_model=TaskOut)
def run_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or task.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.status in ("completed", "running", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Task is {task.status}")
    task = Orchestrator(db).execute_task(task_id)
    return _to_out(db, task)


@router.post("/{task_id}/retry", response_model=TaskOut)
def retry_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or task.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.status not in ("failed", "blocked"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot retry a {task.status} task")
    task.status = "queued"
    task.error = None
    db.commit()
    return _to_out(db, task)


@router.post("/{task_id}/cancel", response_model=TaskOut)
def cancel_task(task_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if task is None or task.org_id != user.org_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
    if task.status in ("completed", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Task already {task.status}")
    task.status = "cancelled"
    db.commit()
    publish(db, EventType.TASK_CANCELLED, {"title": task.title}, org_id=user.org_id, task_id=task.id, commit=True)
    return _to_out(db, task)

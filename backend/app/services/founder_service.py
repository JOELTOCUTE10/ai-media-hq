"""Founder Mode (Section 7): turn a high-level goal into real, linked work.

The plan created here is REAL and deterministic - actual tasks with real
agents, dependencies and permissions, tracked to completion. An optional AI
strategy task (Chief Strategy Agent) enriches the plan when an AI provider is
configured; without one it fails honestly with a setup message.
"""

from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.agent import Agent
from app.models.channel import Channel
from app.models.organization import User
from app.models.task import Goal, Task, TaskDependency
from app.services.event_bus import publish


def _agent(db: Session, org_id: int, key: str) -> Agent | None:
    return db.query(Agent).filter_by(org_id=org_id, key=key).first()


def create_goal(db: Session, user: User, title: str, description: str = "",
                channel_slug: str | None = None, target_date=None) -> Goal:
    org_id = user.org_id
    channel = None
    if channel_slug:
        channel = db.query(Channel).filter_by(org_id=org_id, slug=channel_slug).first()

    goal = Goal(org_id=org_id, title=title, description=description,
                status="active", target_date=target_date)
    db.add(goal)
    db.flush()

    def add_task(agent_key: str, task_title: str, permission: str,
                 depends_on: Task | None = None) -> Task:
        agent = _agent(db, org_id, agent_key)
        t = Task(org_id=org_id, title=task_title,
                 description=f"Founder goal: {title}",
                 assigned_agent_id=agent.id if agent else None,
                 channel_id=channel.id if channel else None,
                 goal_id=goal.id,
                 input={"required_permission": permission, "founder_goal": {"goal_id": goal.id, "title": title}})
        db.add(t)
        db.flush()
        if depends_on is not None:
            db.add(TaskDependency(task_id=t.id, depends_on_id=depends_on.id))
            db.flush()
        return t

    # Deterministic growth plan - real work, runs without an AI key
    research = add_task("web_research", f"Research current trends and opportunities for: {title}",
                        "write_research")
    add_task("trend_intelligence", f"Detect rising trends relevant to: {title}", "read_research")
    ideas = add_task("idea_agent", f"Generate strong content ideas for: {title}",
                     "create_ideas", depends_on=research)
    add_task("content_strategist", f"Build a content plan for: {title}",
             "create_ideas", depends_on=ideas)
    add_task("analytics_agent", f"Analyze recent performance for: {title}", "access_analytics")

    # Optional AI strategy review - enriches the plan when a provider is configured
    add_task("chief_strategy", f"Strategic assessment of goal: {title}", "review_content")

    publish(db, EventType.GOAL_CREATED, {"goal_id": goal.id, "title": title,
                                         "tasks": 6}, org_id=org_id, commit=True)
    return goal


def goal_progress(db: Session, org_id: int, goal: Goal) -> dict:
    tasks = db.query(Task).filter_by(goal_id=goal.id).all()
    done = [t for t in tasks if t.status == "completed"]
    failed = [t for t in tasks if t.status == "failed"]
    return {
        "total": len(tasks), "completed": len(done), "failed": len(failed),
        "in_progress": len(tasks) - len(done) - len(failed),
        "pct": round(100 * len(done) / len(tasks), 1) if tasks else 0.0,
        "task_ids": [t.id for t in tasks],
    }

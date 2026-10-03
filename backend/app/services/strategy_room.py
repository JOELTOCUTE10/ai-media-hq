"""AI Strategy Room (Section 17).

A structured multi-agent decision process - NOT human-like consciousness.
Each reviewer agent independently analyzes an idea through the real
orchestrator; results persist as AgentMessages; a synthesis is produced.
If the AI provider is unconfigured, reviews fail honestly with the reason.
"""
import json

from sqlalchemy.orm import Session

from app.core.events import EventType
from app.models.agent import Agent, AgentMessage
from app.models.content import ContentIdea
from app.models.organization import Organization
from app.models.task import Task
from app.services.event_bus import publish
from app.services.orchestrator import Orchestrator

REVIEWERS = [
    ("chief_strategy", "Is this worth making?", "review_content"),
    ("trend_intelligence", "Is this currently relevant?", "read_research"),
    ("fact_verification", "Can the claims be verified?", "review_content"),
    ("audience_intelligence", "Would the audience likely find this interesting?", "access_analytics"),
    ("production_planner", "Can this be produced efficiently?", "execute_production"),
]


def _agent_by_key(db: Session, org_id: int, key: str) -> Agent | None:
    return db.query(Agent).filter_by(org_id=org_id, key=key).first()


def _msg(db: Session, org_id: int, sender_id, mtype: str, content: dict) -> None:
    db.add(AgentMessage(org_id=org_id, sender_agent_id=sender_id,
                       message_type=mtype, content=json.dumps(content)))


def run_strategy_room(db: Session, org: Organization, idea: ContentIdea) -> dict:
    """Runs every reviewer through the orchestrator and stores the outcome."""
    orch = Orchestrator(db)
    reviews = []
    for agent_key, question, permission in REVIEWERS:
        agent = _agent_by_key(db, org.id, agent_key)
        if agent is None:
            reviews.append({"agent": agent_key, "question": question,
                            "status": "skipped", "detail": "agent not found"})
            continue
        task = Task(org_id=org.id, title=f"Strategy room review: {question}",
                    description=f"Review the idea '{idea.title}' and answer: {question}",
                    assigned_agent_id=agent.id, channel_id=idea.channel_id,
                    input={"required_permission": permission,
                           "strategy_room": {"idea_id": idea.id, "question": question}})
        db.add(task)
        db.flush()
        ran = orch.execute_task(task.id)
        entry = {
            "agent": agent.name, "agent_key": agent_key, "question": question,
            "task_id": ran.id, "task_status": ran.status,
            "answer": (ran.output or {}).get("result", "") if ran.status == "completed" else "",
        }
        if ran.status != "completed":
            entry["error"] = ran.error or "task did not complete"
        reviews.append(entry)
        _msg(db, org.id, agent.id, "strategy_review", {"idea_id": idea.id, **entry})
        db.commit()

    # Synthesis by the Chief Strategy Agent
    synthesis = {"answer": "", "task_status": "skipped"}
    chief = _agent_by_key(db, org.id, "chief_strategy")
    if chief is not None:
        stask = Task(org_id=org.id, title=f"Strategy room synthesis: {idea.title}",
                     description="Synthesize the department reviews into a final go/no-go recommendation.",
                     assigned_agent_id=chief.id, channel_id=idea.channel_id,
                     input={"required_permission": "review_content",
                            "strategy_room": {"idea_id": idea.id, "reviews": [
                                {k: v for k, v in r.items() if k != "task_id"} for r in reviews]}})
        db.add(stask)
        db.flush()
        ran = orch.execute_task(stask.id)
        synthesis = {"task_id": ran.id, "task_status": ran.status,
                     "answer": (ran.output or {}).get("result", "") if ran.status == "completed" else "",
                     "error": ran.error if ran.status != "completed" else ""}
        _msg(db, org.id, chief.id, "strategy_synthesis",
             {"idea_id": idea.id, **synthesis})
        db.commit()

    completed = sum(1 for r in reviews if r["task_status"] == "completed")
    publish(db, EventType.STRATEGY_REVIEW_COMPLETED,
            {"idea_id": idea.id, "reviews_completed": completed, "total": len(REVIEWERS)},
            org_id=org.id, commit=True)

    idea.why_selected = {
        "strategy_room": {"reviews": reviews, "synthesis": synthesis,
                          "completed": completed, "total": len(REVIEWERS)},
    }
    if idea.status == "candidate":
        idea.status = "reviewed"
    db.commit()
    return {"idea_id": idea.id, "completed": completed, "total": len(REVIEWERS),
            "reviews": reviews, "synthesis": synthesis}

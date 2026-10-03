"""Import all models so they register on Base.metadata."""
from app.db.base import Base  # noqa: F401
from app.models.agent import Agent, AgentMessage, AgentPermission, AgentRun  # noqa: F401
from app.models.analytics import AnalyticsSnapshot, Experiment, ExperimentResult, LearningInsight  # noqa: F401
from app.models.channel import Channel  # noqa: F401
from app.models.content import Claim, ContentIdea, Script, ScriptVersion  # noqa: F401
from app.models.knowledge import KnowledgeEntity, KnowledgeRelationship, Memory  # noqa: F401
from app.models.ops import AuditLog, CostRecord, Integration, Schedule, SystemEvent  # noqa: F401
from app.models.organization import Organization, User  # noqa: F401
from app.models.production import (  # noqa: F401
    Approval,
    Asset,
    ProductionJob,
    PublishingJob,
    QualityCheck,
    RightsRecord,
)
from app.models.research import ResearchDocument, ResearchSource, Topic, Trend  # noqa: F401
from app.models.task import Task, TaskDependency, Workflow, WorkflowRun  # noqa: F401

__all__ = ["Base"]

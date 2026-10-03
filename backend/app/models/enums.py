"""Shared enums for the whole application."""
import enum


class UserRole(str, enum.Enum):
    OWNER = "owner"
    ADMIN = "admin"
    VIEWER = "viewer"


class AgentPermissionLevel(str, enum.Enum):
    READ_ONLY = "read_only"
    WORKER = "worker"
    REVIEWER = "reviewer"
    PUBLISHER = "publisher"
    ADMINISTRATOR = "administrator"


class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class RunStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    WAITING = "waiting"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkflowRunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SourceType(str, enum.Enum):
    PRIMARY = "primary"
    OFFICIAL_ORGANIZATION = "official_organization"
    ORIGINAL_RESEARCH = "original_research"
    REPUTABLE_JOURNALISM = "reputable_journalism"
    SECONDARY = "secondary"
    SOCIAL = "social"
    UNKNOWN = "unknown"


class TrendLifecycle(str, enum.Enum):
    EMERGING = "emerging"
    GROWING = "growing"
    STABLE = "stable"
    DECLINING = "declining"


class IdeaStatus(str, enum.Enum):
    RESEARCH = "research"
    CANDIDATE = "candidate"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    PRODUCTION = "production"
    PUBLISHED = "published"
    ANALYZED = "analyzed"
    REJECTED = "rejected"
    ARCHIVED = "archived"


class ClaimStatus(str, enum.Enum):
    VERIFIED = "verified"
    PARTIALLY_SUPPORTED = "partially_supported"
    DISPUTED = "disputed"
    UNSUPPORTED = "unsupported"
    NEEDS_REVIEW = "needs_review"


class ProductionStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RightsStatus(str, enum.Enum):
    USER_OWNED = "user_owned"
    LICENSED = "licensed"
    PERMISSION_GRANTED = "permission_granted"
    PUBLIC_DOMAIN = "public_domain"
    PLATFORM_PERMITTED = "platform_permitted"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"


class QCResult(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CHANGES_REQUESTED = "changes_requested"


class PublishingStatus(str, enum.Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    UPLOADING = "uploading"
    PUBLISHED = "published"
    FAILED = "failed"


class MemoryScope(str, enum.Enum):
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    CHANNEL = "channel"
    AGENT = "agent"
    CONTENT = "content"
    STRATEGIC = "strategic"


class CostCategory(str, enum.Enum):
    MODEL_USAGE = "model_usage"
    VIDEO_GENERATION = "video_generation"
    VOICE_GENERATION = "voice_generation"
    STORAGE = "storage"
    API = "api"
    RESEARCH = "research"
    INFRASTRUCTURE = "infrastructure"


class IntegrationStatus(str, enum.Enum):
    UNCONFIGURED = "unconfigured"
    CONFIGURED = "configured"
    ERROR = "error"


class ExperimentStatus(str, enum.Enum):
    DRAFT = "draft"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

"""Agent permission system (Section 9).

Levels accumulate: each level grants every permission of the level above
nothing - they are explicit sets. Publishing additionally requires human
approval by default (org settings: auto_publish=false).
"""

# Canonical permission vocabulary (Section 9)
READ_RESEARCH = "read_research"
WRITE_RESEARCH = "write_research"
CREATE_IDEAS = "create_ideas"
CREATE_SCRIPTS = "create_scripts"
EXECUTE_PRODUCTION = "execute_production"
ACCESS_ANALYTICS = "access_analytics"
REVIEW_CONTENT = "review_content"
PUBLISH = "publish"
MODIFY_SCHEDULES = "modify_schedules"
SPEND_CREDITS = "spend_credits"
MODIFY_SYSTEM = "modify_system"

ALL_PERMISSIONS = {
    READ_RESEARCH, WRITE_RESEARCH, CREATE_IDEAS, CREATE_SCRIPTS, EXECUTE_PRODUCTION,
    ACCESS_ANALYTICS, REVIEW_CONTENT, PUBLISH, MODIFY_SCHEDULES, SPEND_CREDITS, MODIFY_SYSTEM,
}

LEVEL_PERMISSIONS: dict[str, set[str]] = {
    "read_only": {READ_RESEARCH, ACCESS_ANALYTICS},
    "worker": {READ_RESEARCH, ACCESS_ANALYTICS, WRITE_RESEARCH, CREATE_IDEAS, CREATE_SCRIPTS,
               EXECUTE_PRODUCTION, SPEND_CREDITS},
    "reviewer": {READ_RESEARCH, ACCESS_ANALYTICS, WRITE_RESEARCH, REVIEW_CONTENT},
    "publisher": {READ_RESEARCH, ACCESS_ANALYTICS, MODIFY_SCHEDULES, PUBLISH},
    "administrator": ALL_PERMISSIONS,
}


def agent_can(permission_level: str, permission: str) -> bool:
    return permission in LEVEL_PERMISSIONS.get(permission_level, set())

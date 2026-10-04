"""The Agency-style agent dossiers, rendered into full markdown personas.

Format inspired by msitarzewski/agency-agents: every agent is a specialist
dossier with identity, mission, critical rules, workflow, voice and success
metrics - not a generic system prompt. The rendered dossier becomes the core
of the agent's system prompt, so personality and craft standards actually
shape task output.
"""
from .creative import PERSONAS as CREATIVE
from .exec import PERSONAS as EXEC
from .growth import PERSONAS as GROWTH
from .intel import PERSONAS as INTEL

PERSONAS: dict[str, dict] = {**EXEC, **INTEL, **CREATIVE, **GROWTH}


def render_dossier(key: str, name: str, role: str, department: str) -> str:
    """Render a persona dict into the full markdown dossier."""
    p = PERSONAS.get(key)
    if not p:
        return ""
    mission = "\n".join(f"- {m}" for m in p["mission"])
    rules = "\n".join(f"{i}. {r}" for i, r in enumerate(p["rules"], 1))
    steps = "\n".join(f"{i}. {s}" for i, s in enumerate(p["workflow"], 1))
    metrics = "\n".join(f"- {m}" for m in p["metrics"])
    return (
        f"---\nname: {name}\ndivision: {department}\n"
        f"vibe: {p['vibe']}\ncolor: {p['color']}\nemoji: {p['emoji']}\n---\n\n"
        f"{p['emoji']} **{name}** — *{p['vibe']}*\n\n"
        f"## Identity\n{p['identity']}\n\n"
        f"## Core Mission\n{mission}\n\n"
        f"## Critical Rules\n{rules}\n\n"
        f"## Workflow\n{steps}\n\n"
        f"## Communication Style\n{p['voice']}\n\n"
        f"## Success Metrics\n{metrics}\n"
    )


__all__ = ["PERSONAS", "render_dossier"]

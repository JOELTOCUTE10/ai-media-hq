# Agent Guide

## Organization (33 agents, 8 departments)

executive: Chief Strategy, Chief Operations, Project Manager
intelligence: Web Research, Trend Intelligence, Social Intelligence,
  Competitor Intelligence, Fact Verification, Source Evaluation
creative: Idea, Hook, Script, Storytelling, Content Strategist
production: Production Planner, Video Generation, Editing, Caption, Thumbnail/Visual
quality: Fact Checker, Copyright/Rights, Quality Control, Brand Safety
publishing: Publishing, Scheduling, Metadata
growth: Analytics, Experiment, Optimization, Audience Intelligence
operations: Cost Intelligence, System Health, Daily Report

Each agent has a unique key, name, role, description, capabilities, tools,
permission level, model config and memory access. All live as data in the
`agents` table, seeded from `app/agents/registry.py`.

## Permission levels

| Level | Grants |
|---|---|
| read_only | read_research, access_analytics |
| worker | + write_research, create_ideas, create_scripts, execute_production, spend_credits |
| reviewer | read, analytics, write_research, review_content |
| publisher | read, analytics, modify_schedules, publish |
| administrator | everything incl. modify_system |

Enforcement is server-side in the orchestrator: a task with
`input.required_permission` that the assigned agent lacks is set to `blocked`.

## Communication

Agents communicate through persisted rows, never ephemeral chat memory:
`agent_messages`, `agent_runs`, `system_events` and tasks with dependencies.
Example chain (built from tasks + events): Research -> Trend -> Strategy ->
Idea -> Script -> Fact Checker -> QC -> Approval -> Publishing.

## Runs & observability

Every execution writes an AgentRun (input, output, duration, tokens, cost,
error). Structured JSON logs include task_id / agent_id / status / duration.
Inspect runs via `GET /api/agents/{id}/runs` and events via `GET /api/events`.

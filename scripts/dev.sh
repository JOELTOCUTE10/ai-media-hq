#!/usr/bin/env bash
# Local development helper: backend on :8000, frontend on :5173
set -e
cd "$(dirname "$0")/.."
(cd backend && [ -f .env ] || cp ../.env.example .env 2>/dev/null || true)
(cd backend && uvicorn app.main:app --reload --port 8000 &
 (cd frontend && npm install --silent && npm run dev))

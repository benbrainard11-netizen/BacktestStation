#!/usr/bin/env bash
# Regenerate shared/openapi.json from FastAPI and frontend TS types from it.
#
# Run whenever you change a Pydantic schema or add/remove an endpoint.
# The output files are committed to git so CI and collaborators always
# have an up-to-date snapshot.
#
#   shared/openapi.json           -- FastAPI OpenAPI schema (source of truth)
#   frontend/lib/api/generated.ts -- auto-generated TS types
#
# Prereqs:
#   - backend venv with the app installed (`pip install -e "backend[dev]"`)
#   - `npm install` in frontend/ (openapi-typescript is a devDependency)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "→ export OpenAPI schema"
(
  cd backend
  if [ -x ".venv/Scripts/python.exe" ]; then
    PY=".venv/Scripts/python.exe"
  elif [ -x ".venv/bin/python" ]; then
    PY=".venv/bin/python"
  else
    echo "no backend venv at backend/.venv — create one first" >&2
    exit 1
  fi
  "$PY" -m app.cli.export_openapi
)

echo "→ generate TypeScript types"
(
  cd frontend
  npm run --silent generate-types
)

echo "✓ done. Review the diff:"
echo "  git diff shared/openapi.json frontend/lib/api/generated.ts"

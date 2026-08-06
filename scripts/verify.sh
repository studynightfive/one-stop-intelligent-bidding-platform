#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

"$SCRIPT_DIR/check-environment.sh"
"$SCRIPT_DIR/validate-contract.sh"

front_before=$(sha256sum "$ROOT/demo/src/api/generated/schema.ts" | cut -d ' ' -f 1)
back_before=$(sha256sum "$ROOT/backend/app/contracts/generated/models.py" | cut -d ' ' -f 1)
"$SCRIPT_DIR/generate-contracts.sh"
front_after=$(sha256sum "$ROOT/demo/src/api/generated/schema.ts" | cut -d ' ' -f 1)
back_after=$(sha256sum "$ROOT/backend/app/contracts/generated/models.py" | cut -d ' ' -f 1)
[ "$front_before" = "$front_after" ] && [ "$back_before" = "$back_after" ] || {
  echo 'Generated contract files were stale.' >&2
  exit 1
}

cd "$ROOT/backend"
"$SCRIPT_DIR/uv.sh" run --frozen ruff check app tests migrations
"$SCRIPT_DIR/uv.sh" run --frozen ruff format --check app tests migrations
"$SCRIPT_DIR/uv.sh" run --frozen mypy app
"$SCRIPT_DIR/uv.sh" run --frozen pytest
"$SCRIPT_DIR/uv.sh" run --frozen alembic heads

cd "$ROOT/demo"
npm run typecheck
npm run lint
npm run test
npm run build

cd "$ROOT"
docker compose --env-file .env.example -f infra/compose.yaml config --quiet
git diff --check
echo '[OK] Full L0 foundation verification passed'

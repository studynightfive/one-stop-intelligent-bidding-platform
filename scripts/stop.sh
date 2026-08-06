#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

if [ ! -f "$ROOT/.env" ]; then
  echo '.env does not exist; nothing was initialized' >&2
  exit 1
fi

docker compose --env-file "$ROOT/.env" -f "$ROOT/infra/compose.yaml" down --remove-orphans
echo '[OK] Core stack stopped; named data volumes were preserved'

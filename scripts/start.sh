#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
ENV_FILE="$ROOT/.env"
COMPOSE_FILE="$ROOT/infra/compose.yaml"

"$SCRIPT_DIR/bootstrap.sh"

if ! docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d \
  postgres redis minio minio-init mailpit api web; then
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --no-color --tail 200
  exit 1
fi

attempt=1
while [ "$attempt" -le 60 ]; do
  if curl --fail --silent --show-error http://127.0.0.1:8210/api/v1/openapi.json >/dev/null 2>&1 && \
    curl --fail --silent --show-error http://127.0.0.1:3210/healthz >/dev/null 2>&1; then
    echo '[OK] Core stack is healthy'
    echo 'Demo:     http://127.0.0.1:3210'
    echo 'API docs: http://127.0.0.1:8210/docs'
    echo 'Mailpit:  http://127.0.0.1:58025'
    echo 'MinIO:    http://127.0.0.1:59001'
    exit 0
  fi
  sleep 3
  attempt=$((attempt + 1))
done

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs --no-color --tail 200
echo 'Core stack did not become healthy within 180 seconds' >&2
exit 1

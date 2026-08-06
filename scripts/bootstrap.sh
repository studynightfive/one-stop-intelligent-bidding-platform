#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
SECRET_DIR="$ROOT/infra/secrets/dev"

"$SCRIPT_DIR/check-environment.sh"

if [ ! -f "$ROOT/.env" ]; then
  cp "$ROOT/.env.example" "$ROOT/.env"
  echo '[CREATE] .env from .env.example'
else
  echo '[KEEP] existing .env'
fi

mkdir -p "$SECRET_DIR"
if [ ! -f "$SECRET_DIR/jwt_private_key" ] || [ ! -f "$SECRET_DIR/jwt_public_key" ]; then
  openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out "$SECRET_DIR/jwt_private_key"
  openssl pkey -in "$SECRET_DIR/jwt_private_key" -pubout -out "$SECRET_DIR/jwt_public_key"
  echo '[CREATE] local RSA signing key pair'
else
  echo '[KEEP] existing local RSA signing key pair'
fi
if [ ! -f "$SECRET_DIR/model_master_key" ]; then
  openssl rand -base64 32 > "$SECRET_DIR/model_master_key"
  echo '[CREATE] local model master key'
else
  echo '[KEEP] existing local model master key'
fi
chmod 600 "$SECRET_DIR"/*

cd "$ROOT/backend"
"$SCRIPT_DIR/uv.sh" sync --frozen
cd "$ROOT/demo"
npm ci --ignore-scripts

"$SCRIPT_DIR/generate-contracts.sh"
"$SCRIPT_DIR/validate-contract.sh"
cd "$ROOT"
docker compose --env-file .env -f infra/compose.yaml config --quiet

echo '[OK] Bootstrap complete.'

#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

cd "$ROOT/demo"
npm run contract:generate

cd "$ROOT/backend"
"$SCRIPT_DIR/uv.sh" run --frozen datamodel-codegen \
  --input ../contracts/openapi.yaml \
  --input-file-type openapi \
  --output app/contracts/generated/models.py \
  --output-model-type pydantic_v2.BaseModel \
  --target-python-version 3.11 \
  --use-standard-collections \
  --use-union-operator \
  --use-schema-description \
  --use-field-description \
  --disable-timestamp

echo '[OK] Frontend and backend contracts generated from contracts/openapi.yaml'

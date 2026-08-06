#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
cd "$ROOT"

assert_exact() {
  name=$1
  actual=$2
  expected=$3
  if [ "$actual" != "$expected" ]; then
    echo "$name version mismatch: expected $expected, got $actual" >&2
    exit 1
  fi
  echo "[OK] $name $expected"
}

assert_exact "Node.js" "$(node --version)" "v24.16.0"
assert_exact "npm" "$(npm --version)" "11.13.0"
assert_exact "uv wrapper" "$($SCRIPT_DIR/uv.sh --version)" "uv 0.5.11 (c4d0caaee 2024-12-19)"
assert_exact "Python" "$($SCRIPT_DIR/uv.sh run --python 3.11.11 python --version 2>&1)" "Python 3.11.11"

version_at_least() {
  actual=$1
  minimum=$2
  awk -v actual="$actual" -v minimum="$minimum" 'BEGIN {
    split(actual, a, "."); split(minimum, b, ".")
    for (i = 1; i <= 4; i++) {
      av = a[i] + 0; bv = b[i] + 0
      if (av > bv) exit 0
      if (av < bv) exit 1
    }
    exit 0
  }'
}

openssl_version=$(openssl version | sed -E 's/^OpenSSL ([0-9.]+).*/\1/')
echo "[OK] OpenSSL $openssl_version"

docker_version=$(docker --version | sed -E 's/^Docker version ([0-9.]+).*/\1/')
compose_version=$(docker compose version --short | sed 's/^v//')
if ! version_at_least "$docker_version" "27.0.0"; then
  echo "Docker must be >= 27.0.0, got $docker_version" >&2
  exit 1
fi
if ! version_at_least "$compose_version" "2.29.0"; then
  echo "Docker Compose must be >= 2.29.0, got $compose_version" >&2
  exit 1
fi
echo "[OK] Docker $docker_version"
echo "[OK] Docker Compose $compose_version"

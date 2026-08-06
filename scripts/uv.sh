#!/usr/bin/env sh
set -eu

exec uvx --from 'uv==0.5.11' uv "$@"

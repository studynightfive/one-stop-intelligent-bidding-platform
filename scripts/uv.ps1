$ErrorActionPreference = 'Stop'

& uvx --from 'uv==0.5.11' uv @args
exit $LASTEXITCODE

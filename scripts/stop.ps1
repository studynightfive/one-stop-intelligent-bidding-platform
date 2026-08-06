$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$composePath = Join-Path $repoRoot 'infra/compose.yaml'

if (-not (Test-Path -LiteralPath $envPath)) {
    throw '.env does not exist; nothing was initialized'
}

& docker compose --env-file $envPath -f $composePath down --remove-orphans
if ($LASTEXITCODE -ne 0) { throw 'Core stack failed to stop cleanly' }
Write-Host '[OK] Core stack stopped; named data volumes were preserved'

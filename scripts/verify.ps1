param(
    [switch]$IncludeE2E
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

& $PSScriptRoot/check-environment.ps1
& $PSScriptRoot/validate-contract.ps1

$frontGenerated = Join-Path $repoRoot 'demo/src/api/generated/schema.ts'
$backGenerated = Join-Path $repoRoot 'backend/app/contracts/generated/models.py'
$frontBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $frontGenerated).Hash
$backBefore = (Get-FileHash -Algorithm SHA256 -LiteralPath $backGenerated).Hash
& $PSScriptRoot/generate-contracts.ps1
$frontAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $frontGenerated).Hash
$backAfter = (Get-FileHash -Algorithm SHA256 -LiteralPath $backGenerated).Hash
if ($frontBefore -ne $frontAfter -or $backBefore -ne $backAfter) {
    throw 'Generated contract files were stale. Review and commit the regenerated files, then run verify again.'
}
Write-Host '[OK] Generated contracts are deterministic and current'

Push-Location "$repoRoot/backend"
try {
    & $PSScriptRoot/uv.ps1 run --frozen ruff check app tests migrations
    if ($LASTEXITCODE -ne 0) { throw 'Backend lint failed' }
    & $PSScriptRoot/uv.ps1 run --frozen ruff format --check app tests migrations
    if ($LASTEXITCODE -ne 0) { throw 'Backend format check failed' }
    & $PSScriptRoot/uv.ps1 run --frozen mypy app
    if ($LASTEXITCODE -ne 0) { throw 'Backend typecheck failed' }
    & $PSScriptRoot/uv.ps1 run --frozen pytest
    if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed' }
    & $PSScriptRoot/uv.ps1 run --frozen alembic heads
    if ($LASTEXITCODE -ne 0) { throw 'Alembic head check failed' }
}
finally {
    Pop-Location
}

Push-Location "$repoRoot/demo"
try {
    & npm run typecheck
    if ($LASTEXITCODE -ne 0) { throw 'Frontend typecheck failed' }
    & npm run lint
    if ($LASTEXITCODE -ne 0) { throw 'Frontend lint failed' }
    & npm run test
    if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed' }
    & npm run build
    if ($LASTEXITCODE -ne 0) { throw 'Frontend build failed' }
}
finally {
    Pop-Location
}

Push-Location "$repoRoot/e2e"
try {
    & npm run typecheck
    if ($LASTEXITCODE -ne 0) { throw 'E2E typecheck failed' }
    & npm run lint
    if ($LASTEXITCODE -ne 0) { throw 'E2E lint failed' }
    if ($IncludeE2E) {
        $apiPort = if ($env:API_PORT) { $env:API_PORT } else { '8210' }
        $webPort = if ($env:WEB_PORT) { $env:WEB_PORT } else { '3210' }
        $apiBaseUrl = if ($env:E2E_API_URL) { $env:E2E_API_URL.TrimEnd('/') } else { "http://127.0.0.1:$apiPort" }
        $webBaseUrl = if ($env:E2E_BASE_URL) { $env:E2E_BASE_URL.TrimEnd('/') } else { "http://127.0.0.1:$webPort" }
        try {
            Invoke-WebRequest -Uri "$apiBaseUrl/api/v1/health/ready" -UseBasicParsing -TimeoutSec 3 | Out-Null
            Invoke-WebRequest -Uri "$webBaseUrl/healthz" -UseBasicParsing -TimeoutSec 3 | Out-Null
        }
        catch {
            throw "E2E requires a healthy local stack at Web $webBaseUrl and API $apiBaseUrl. Start it first or set WEB_PORT/API_PORT."
        }
        & npm run test
        if ($LASTEXITCODE -ne 0) { throw 'E2E tests failed' }
    }
}
finally {
    Pop-Location
}

& docker compose --env-file "$repoRoot/.env.example" -f "$repoRoot/infra/compose.yaml" config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose validation failed' }

Push-Location $repoRoot
try {
    & git diff --check
    if ($LASTEXITCODE -ne 0) { throw 'Git whitespace check failed' }
}
finally {
    Pop-Location
}

if ($IncludeE2E) {
    Write-Host '[OK] Full L0 verification, including real E2E, passed'
}
else {
    Write-Host '[OK] Full L0 foundation verification passed (use -IncludeE2E with the default local stack for browser flows)'
}

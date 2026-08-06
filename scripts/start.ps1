$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$composePath = Join-Path $repoRoot 'infra/compose.yaml'
$services = @('postgres', 'redis', 'minio', 'minio-init', 'mailpit', 'api', 'web')

& (Join-Path $PSScriptRoot 'bootstrap.ps1')

& docker compose --env-file $envPath -f $composePath up -d @services
if ($LASTEXITCODE -ne 0) {
    & docker compose --env-file $envPath -f $composePath ps
    & docker compose --env-file $envPath -f $composePath logs --no-color --tail 200
    throw 'Core stack failed to start'
}

$ready = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $api = Invoke-WebRequest -Uri 'http://127.0.0.1:8210/api/v1/openapi.json' -UseBasicParsing -TimeoutSec 2
        $web = Invoke-WebRequest -Uri 'http://127.0.0.1:3210/healthz' -UseBasicParsing -TimeoutSec 2
        if ($api.StatusCode -eq 200 -and $web.StatusCode -eq 200) {
            $ready = $true
            break
        }
    }
    catch {
        Start-Sleep -Seconds 3
    }
}

if (-not $ready) {
    & docker compose --env-file $envPath -f $composePath ps
    & docker compose --env-file $envPath -f $composePath logs --no-color --tail 200
    throw 'Core stack did not become healthy within 180 seconds'
}

Write-Host '[OK] Core stack is healthy'
Write-Host 'Demo:     http://127.0.0.1:3210'
Write-Host 'API docs: http://127.0.0.1:8210/docs'
Write-Host 'Mailpit:  http://127.0.0.1:58025'
Write-Host 'MinIO:    http://127.0.0.1:59001'

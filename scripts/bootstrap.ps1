$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $repoRoot '.env'
$envExamplePath = Join-Path $repoRoot '.env.example'
$secretDir = Join-Path $repoRoot 'infra/secrets/dev'
$openssl = (Get-Command openssl -ErrorAction Stop).Source

& $PSScriptRoot/check-environment.ps1

if (-not (Test-Path -LiteralPath $envPath)) {
    Copy-Item -LiteralPath $envExamplePath -Destination $envPath
    Write-Host '[CREATE] .env from .env.example'
}
else {
    Write-Host '[KEEP] existing .env'
}

New-Item -ItemType Directory -Path $secretDir -Force | Out-Null
$privateKeyPath = Join-Path $secretDir 'jwt_private_key'
$publicKeyPath = Join-Path $secretDir 'jwt_public_key'
$masterKeyPath = Join-Path $secretDir 'model_master_key'

if (-not (Test-Path -LiteralPath $privateKeyPath) -or -not (Test-Path -LiteralPath $publicKeyPath)) {
    & $openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:3072 -out $privateKeyPath
    if ($LASTEXITCODE -ne 0) { throw 'Failed to generate the local RSA private key' }
    & $openssl pkey -in $privateKeyPath -pubout -out $publicKeyPath
    if ($LASTEXITCODE -ne 0) { throw 'Failed to derive the local RSA public key' }
    Write-Host '[CREATE] local RSA signing key pair'
}
else {
    Write-Host '[KEEP] existing local RSA signing key pair'
}

if (-not (Test-Path -LiteralPath $masterKeyPath)) {
    & $openssl rand -base64 -out $masterKeyPath 32
    if ($LASTEXITCODE -ne 0) { throw 'Failed to generate the local model master key' }
    Write-Host '[CREATE] local model master key'
}
else {
    Write-Host '[KEEP] existing local model master key'
}

Push-Location "$repoRoot/backend"
try {
    & $PSScriptRoot/uv.ps1 sync --frozen
    if ($LASTEXITCODE -ne 0) { throw 'uv sync failed' }
}
finally {
    Pop-Location
}

Push-Location "$repoRoot/demo"
try {
    & npm ci --ignore-scripts
    if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
}
finally {
    Pop-Location
}

& $PSScriptRoot/generate-contracts.ps1
& $PSScriptRoot/validate-contract.ps1
& docker compose --env-file $envPath -f "$repoRoot/infra/compose.yaml" config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose validation failed' }

Write-Host '[OK] Bootstrap complete. Start the core stack with:'
Write-Host 'docker compose --env-file .env -f infra/compose.yaml up -d postgres redis minio minio-init mailpit api web'

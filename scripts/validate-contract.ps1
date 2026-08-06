$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location "$repoRoot/backend"
try {
    & $PSScriptRoot/uv.ps1 run --frozen python ../scripts/validate_contract.py
    if ($LASTEXITCODE -ne 0) { throw 'Contract validation failed' }
}
finally {
    Pop-Location
}

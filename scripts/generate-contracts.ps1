$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

Push-Location "$repoRoot/demo"
try {
    & npm run contract:generate
    if ($LASTEXITCODE -ne 0) { throw 'Frontend contract generation failed' }
}
finally {
    Pop-Location
}

Push-Location "$repoRoot/backend"
try {
    & $PSScriptRoot/uv.ps1 run --frozen datamodel-codegen `
        --input ../contracts/openapi.yaml `
        --input-file-type openapi `
        --output app/contracts/generated/models.py `
        --output-model-type pydantic_v2.BaseModel `
        --target-python-version 3.11 `
        --use-standard-collections `
        --use-union-operator `
        --use-schema-description `
        --use-field-description `
        --disable-timestamp
    if ($LASTEXITCODE -ne 0) { throw 'Backend contract generation failed' }
}
finally {
    Pop-Location
}

Write-Host '[OK] Frontend and backend contracts generated from contracts/openapi.yaml'

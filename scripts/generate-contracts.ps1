$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$utf8NoBom = [System.Text.UTF8Encoding]::new($false)

function Convert-ToLf {
    param([string]$Path)

    $content = [System.IO.File]::ReadAllText($Path)
    $normalized = $content.Replace("`r`n", "`n").Replace("`r", "`n")
    [System.IO.File]::WriteAllText($Path, $normalized, $utf8NoBom)
}

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

Convert-ToLf (Join-Path $repoRoot 'demo/src/api/generated/schema.ts')
Convert-ToLf (Join-Path $repoRoot 'backend/app/contracts/generated/models.py')

Write-Host '[OK] Frontend and backend contracts generated from contracts/openapi.yaml'

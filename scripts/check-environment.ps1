$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot

function Assert-ExactVersion {
    param(
        [string]$Name,
        [string]$Actual,
        [string]$Expected
    )
    if ($Actual.Trim() -ne $Expected) {
        throw "$Name version mismatch: expected $Expected, got $Actual"
    }
    Write-Host "[OK] $Name $Expected"
}

Push-Location $repoRoot
try {
    Assert-ExactVersion 'Node.js' (& node --version) 'v24.16.0'
    Assert-ExactVersion 'npm' (& npm --version) '11.13.0'
    $uvVersion = (& $PSScriptRoot/uv.ps1 --version)
    if ($uvVersion -notmatch '^uv 0\.5\.11(?:\s+\(.+\))?$') {
        throw "uv wrapper version mismatch: expected 0.5.11, got $uvVersion"
    }
    Write-Host '[OK] uv wrapper 0.5.11'
    Assert-ExactVersion 'Python' (& $PSScriptRoot/uv.ps1 run --python 3.11.11 python --version) 'Python 3.11.11'

    $opensslVersion = (& openssl version)
    if ($LASTEXITCODE -ne 0 -or $opensslVersion -notmatch '^OpenSSL\s+([0-9.]+)') {
        throw 'OpenSSL is required to create local-only development keys'
    }
    Write-Host "[OK] OpenSSL $($Matches[1])"

    $dockerVersionText = (& docker --version)
    if ($dockerVersionText -notmatch 'Docker version ([0-9.]+)') {
        throw "Unable to parse Docker version: $dockerVersionText"
    }
    if ([version]$Matches[1] -lt [version]'27.0.0') {
        throw "Docker must be >= 27.0.0, got $($Matches[1])"
    }
    Write-Host "[OK] Docker $($Matches[1])"

    $composeVersion = (& docker compose version --short).TrimStart('v')
    if ([version]$composeVersion -lt [version]'2.29.0') {
        throw "Docker Compose must be >= 2.29.0, got $composeVersion"
    }
    Write-Host "[OK] Docker Compose $composeVersion"
}
finally {
    Pop-Location
}

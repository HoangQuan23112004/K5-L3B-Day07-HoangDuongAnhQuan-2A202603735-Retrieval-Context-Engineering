# Invoke from any directory: ./scripts/run.ps1 validate
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$runtimePath = Join-Path $projectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $runtimePath)) {
    $runtimePath = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python311/python.exe'
}
if (-not (Test-Path -LiteralPath $runtimePath)) {
    throw 'Create .venv with Python 3.11+ first; see docs/RUNBOOK.md.'
}
Push-Location $projectRoot
try {
    & $runtimePath -X utf8 -m src.rag @args
    exit $LASTEXITCODE
} finally {
    Pop-Location
}

[CmdletBinding()]
param()

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment is missing. Run scripts\setup.ps1 first."
}
if (-not (Test-Path (Join-Path $ProjectRoot "backend\.env"))) {
    throw "backend\.env is missing. Configure it before migrating."
}

Push-Location $ProjectRoot
try {
    & $VenvPython -m alembic -c alembic.ini upgrade head
} finally {
    Pop-Location
}

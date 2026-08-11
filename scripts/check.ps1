[CmdletBinding()]
param(
    [switch]$RunTests,
    [switch]$CheckApi,
    [string]$ApiBaseUrl = "http://127.0.0.1:8000"
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment is missing. Run scripts\setup.ps1 first."
}
if (-not (Test-Path (Join-Path $ProjectRoot "backend\.env"))) {
    throw "backend\.env is missing."
}

Push-Location $ProjectRoot
try {
    $PreviousPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = (Join-Path $ProjectRoot "backend")
    & $VenvPython -c "from app.core.config import settings; from app.database.database import check_database_connection; print('database_url_configured=' + str(bool(settings.database_url))); print('database_connected=' + str(check_database_connection()))"
    $env:PYTHONPATH = $PreviousPythonPath
    & $VenvPython -m alembic -c alembic.ini current
    if ($RunTests) { & $VenvPython -m pytest backend/tests -q }
    if ($CheckApi) { Invoke-RestMethod "$($ApiBaseUrl.TrimEnd('/'))/api/health" | ConvertTo-Json }
} finally {
    $env:PYTHONPATH = $PreviousPythonPath
    Pop-Location
}

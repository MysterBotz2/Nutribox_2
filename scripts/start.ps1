[CmdletBinding()]
param(
    [string]$HostAddress = "0.0.0.0",
    [ValidateRange(1, 65535)]
    [int]$Port = 8000
)

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    throw "Virtual environment is missing. Run scripts\setup.ps1 first."
}
if (-not (Test-Path (Join-Path $ProjectRoot "backend\.env"))) {
    throw "backend\.env is missing. Configure it before starting the API."
}

Push-Location $ProjectRoot
try {
    & $VenvPython -m uvicorn app.main:app --app-dir backend --host $HostAddress --port $Port
} finally {
    Pop-Location
}

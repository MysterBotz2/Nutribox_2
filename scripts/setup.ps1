[CmdletBinding()]
param()

$ProjectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    $PythonLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -eq $PythonLauncher) {
        throw "Python 3.11 or newer is required. Install Python, then run this script again."
    }
    & py -m venv (Join-Path $ProjectRoot ".venv")
}

& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $ProjectRoot "requirements.txt")

$EnvironmentFile = Join-Path $ProjectRoot "backend\.env"
if (-not (Test-Path $EnvironmentFile)) {
    Write-Warning "backend\.env is missing. Copy .env.example to backend\.env and configure DATABASE_URL and JWT_SECRET_KEY."
} else {
    Write-Host "Environment file found. Values were not displayed."
}

Write-Host "Next: run scripts\migrate.ps1, then scripts\start.ps1."

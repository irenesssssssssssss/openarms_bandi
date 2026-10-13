$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Creazione ambiente Python fallita.' }
}
$monitorPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $monitorPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Installazione dipendenze fallita.' }
if (-not (Test-Path '.env')) { Copy-Item '.env.example' '.env' }
Write-Host 'Apri http://127.0.0.1:8000 e lascia aperta questa finestra.'
& $monitorPython -m uvicorn app:app --host 127.0.0.1 --port 8000 --workers 1

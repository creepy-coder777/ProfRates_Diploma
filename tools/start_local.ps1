$ErrorActionPreference = 'Stop'
Set-Location (Split-Path $PSScriptRoot -Parent)
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    python -m venv .venv
    if ($LASTEXITCODE -ne 0) { exit 1 }
}
& .venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { exit 1 }
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
    Write-Host 'Configure .env: use the same server name as SSMS; save, then run START.cmd again.'
    exit 1
}
& .venv\Scripts\python.exe -X utf8 -m tools.check_db
if ($LASTEXITCODE -ne 0) { exit 1 }
& .venv\Scripts\python.exe -X utf8 -m tools.check_student3
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Inspect the CHECK messages above. Do not execute migration 02 automatically; it changes rating views.'
    exit 1
}
Write-Host 'Frontend: http://127.0.0.1:8000/  API: http://127.0.0.1:8000/docs'
& .venv\Scripts\python.exe -X utf8 -m tools.check_auth_schema
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host 'Real database authentication is enabled. Use the documented local CLI to create or recover an administrator.'
Write-Host 'Local mail: private files under var/mailbox. No real email is sent in this mode.'
& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000

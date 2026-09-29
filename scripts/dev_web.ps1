param([int]$BackendPort = 8000, [int]$FrontendPort = 5173)
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $Python)) { throw 'Python virtual environment not found. Install project dependencies first.' }
if (-not (Test-Path -LiteralPath (Join-Path $Root 'web\node_modules'))) {
  Push-Location (Join-Path $Root 'web')
  try { npm install } finally { Pop-Location }
}
Write-Host "Frontend: http://localhost:$FrontendPort" -ForegroundColor Cyan
Write-Host "Backend:  http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Warning 'Development backend reload clears in-memory rooms.'
$env:HOST = '127.0.0.1'
$env:PORT = [string]$BackendPort
$backend = Start-Process -FilePath $Python -ArgumentList @('-m','uvicorn','sanguosha.web.app:app','--host','127.0.0.1','--port',[string]$BackendPort,'--reload') -WorkingDirectory $Root -NoNewWindow -PassThru
try {
  Push-Location (Join-Path $Root 'web')
  npm run dev -- --port $FrontendPort
} finally {
  Pop-Location
  if (-not $backend.HasExited) { Stop-Process -Id $backend.Id -Force }
}

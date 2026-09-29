$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Write-Host "Checking Cloudflare local deployment prerequisites..."
if (-not (Get-Command node -ErrorAction SilentlyContinue)) { throw 'node is required' }
if (-not (Test-Path (Join-Path $root 'web\package.json'))) { throw 'web package missing' }
if (-not (Test-Path (Join-Path $root 'cloudflare\game-room\wrangler.jsonc'))) { throw 'GameRoom Wrangler config missing' }
Push-Location (Join-Path $root 'web'); npm run build; Pop-Location
Write-Host 'Preflight passed. A later deploy command may require wrangler login.'

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location (Join-Path $root 'web'); $env:CLOUDFLARE_ROOMS = '1'; npm run build; Pop-Location
Push-Location (Join-Path $root 'cloudflare\game-room')
if (-not (Get-Command pywrangler -ErrorAction SilentlyContinue)) { throw 'pywrangler is required; install the Workers project environment first.' }
Write-Host 'The next command contacts Cloudflare and may open an OAuth flow.'
pywrangler deploy
Pop-Location

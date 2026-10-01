$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$web = Join-Path $project 'web'
$python = Join-Path $project '.venv\Scripts\python.exe'
$vite = Join-Path $web 'node_modules\vite\bin\vite.js'
$stateDir = Join-Path $env:LOCALAPPDATA 'SanguoshaLvbuPreview'
$stateFile = Join-Path $stateDir 'processes.json'
$url = 'http://127.0.0.1:5173/t11/god-lvbu-preview'

function PortOpen([int]$port) {
  $client = [System.Net.Sockets.TcpClient]::new()
  try { $result = $client.BeginConnect('127.0.0.1', $port, $null, $null); return $result.AsyncWaitHandle.WaitOne(400) -and $client.Connected }
  catch { return $false }
  finally { $client.Dispose() }
}

function OwnedProcess($record) {
  if (-not $record) { return $null }
  $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
  if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$record.started) { return $process }
  return $null
}

if (Test-Path -LiteralPath $stateFile) {
  try {
    $state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
    if ((OwnedProcess $state.backend) -and (OwnedProcess $state.frontend) -and (PortOpen 8000) -and (PortOpen 5173)) {
      Write-Host "神吕布预览已在运行：$url"
      Start-Process $url
      exit 0
    }
  } catch { }
  Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
}

if ((PortOpen 8000) -or (PortOpen 5173)) {
  Write-Error '端口 8000 或 5173 已被其他服务占用。请先关闭占用端口的服务，然后重试；不会启动重复进程。'
  exit 1
}
if (-not (Test-Path -LiteralPath $python)) { Write-Error "缺少本地 Python 环境：$python"; exit 1 }
if (-not (Test-Path -LiteralPath $vite)) { Write-Error "缺少已安装的 Web 依赖：$vite"; exit 1 }
$node = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
if (-not $node) { Write-Error '找不到 node.exe。请安装或配置项目所需 Node.js。'; exit 1 }

New-Item -ItemType Directory -Path $stateDir -Force | Out-Null
$backend = $null
$frontend = $null
try {
  $backend = Start-Process -FilePath $python -ArgumentList @('-m','uvicorn','sanguosha.web.app:app','--host','127.0.0.1','--port','8000') -WorkingDirectory $project -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stateDir 'backend.out.log') -RedirectStandardError (Join-Path $stateDir 'backend.err.log') -PassThru
  $frontend = Start-Process -FilePath $node -ArgumentList @($vite,'--host','127.0.0.1','--port','5173','--strictPort') -WorkingDirectory $web -WindowStyle Hidden -RedirectStandardOutput (Join-Path $stateDir 'frontend.out.log') -RedirectStandardError (Join-Path $stateDir 'frontend.err.log') -PassThru
  $state = @{ backend = @{ pid = $backend.Id; started = $backend.StartTime.ToUniversalTime().Ticks }; frontend = @{ pid = $frontend.Id; started = $frontend.StartTime.ToUniversalTime().Ticks } }
  $state | ConvertTo-Json | Set-Content -LiteralPath $stateFile -Encoding UTF8
  $ready = $false
  for ($attempt = 0; $attempt -lt 60; $attempt++) {
    if ($backend.HasExited -or $frontend.HasExited) { break }
    if ((PortOpen 8000) -and (PortOpen 5173)) { $ready = $true; break }
    Start-Sleep -Milliseconds 500
  }
  if (-not $ready) { throw "本地服务未能启动。日志位于 $stateDir" }
  Write-Host "神吕布预览已启动：$url"
  Write-Host '双击 STOP_PREVIEW.cmd 可关闭本次启动的服务。'
  Start-Process $url
} catch {
  if ($frontend -and -not $frontend.HasExited) { Stop-Process -Id $frontend.Id -Force -ErrorAction SilentlyContinue }
  if ($backend -and -not $backend.HasExited) { Stop-Process -Id $backend.Id -Force -ErrorAction SilentlyContinue }
  Remove-Item -LiteralPath $stateFile -Force -ErrorAction SilentlyContinue
  Write-Error $_
  exit 1
}

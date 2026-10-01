$ErrorActionPreference = 'Stop'
$stateDir = Join-Path $env:LOCALAPPDATA 'SanguoshaLvbuPreview'
$stateFile = Join-Path $stateDir 'processes.json'
if (-not (Test-Path -LiteralPath $stateFile)) { Write-Host '没有由 preview_lvbu.cmd 启动的服务。'; exit 0 }
$state = Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json
foreach ($record in @($state.frontend, $state.backend)) {
  $process = Get-Process -Id ([int]$record.pid) -ErrorAction SilentlyContinue
  if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq [long]$record.started) {
    Stop-Process -Id $process.Id -Force
  }
}
Remove-Item -LiteralPath $stateFile -Force
Write-Host '本次神吕布本地预览服务已关闭。'

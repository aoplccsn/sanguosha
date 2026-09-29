$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$Version = python -c "from sanguosha.version import APP_VERSION; print(APP_VERSION)"
$Commit = git rev-parse HEAD
Remove-Item -LiteralPath "$Root\build" -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath "$Root\dist" -Recurse -Force -ErrorAction SilentlyContinue
python -m PyInstaller --noconfirm "$Root\sanguosha.spec"
$Bundle = "$Root\dist\Sanguosha-Windows-x64"
$Required = @("Sanguosha.exe", "_internal\assets\manifest.json", "_internal\config\defaults.json")
foreach ($Relative in $Required) {
    if (-not (Test-Path -LiteralPath (Join-Path $Bundle $Relative))) {
        throw "Missing runtime asset: $Relative"
    }
}
@"
1. 解压 ZIP。
2. 双击 Sanguosha.exe。
3. 创建公网房间或加入公网房间。
4. 加入时输入房间码。
5. 公网 Relay 使用出站连接，通常无需开放 Windows 防火墙入站端口。
6. 错误日志位于 %LOCALAPPDATA%\Sanguosha\logs\。
"@ | Set-Content -LiteralPath (Join-Path $Bundle "README.txt") -Encoding UTF8
python "$Root\scripts\frozen_smoke.py" (Join-Path $Bundle "Sanguosha.exe")
$Zip = "$Root\dist\Sanguosha-Windows-x64.zip"
Compress-Archive -LiteralPath $Bundle -DestinationPath $Zip -CompressionLevel Optimal
$Hash = (Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash.ToLowerInvariant()
$Manifest = [ordered]@{ filename = (Split-Path -Leaf $Zip); version = $Version; sha256 = $Hash; build_commit = $Commit }
$Manifest | ConvertTo-Json | Set-Content -LiteralPath "$Root\dist\release-manifest.json" -Encoding UTF8
Write-Host "Built $Zip"
Write-Host "SHA-256 $Hash"

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root "data\runtime\server.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "MAC Analyzer backend is already stopped."
    exit 0
}

$backendPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
$process = Get-Process -Id $backendPid -ErrorAction SilentlyContinue
if ($process) {
    Stop-Process -Id $backendPid
    [void]$process.WaitForExit(5000)
    Write-Output "MAC Analyzer backend stopped: PID $backendPid"
} else {
    Write-Output "Backend process $backendPid is not running."
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

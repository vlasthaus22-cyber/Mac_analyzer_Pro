$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$pidFile = Join-Path $root "data\runtime\server.pid"

if (-not (Test-Path -LiteralPath $pidFile)) {
    Write-Output "Server PID file was not found. The backend may already be stopped."
    exit 0
}

$serverPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
$process = Get-Process -Id $serverPid -ErrorAction SilentlyContinue
if ($null -ne $process) {
    Stop-Process -Id $serverPid
    [void]$process.WaitForExit(5000)
    Write-Output "MAC Analyzer backend stopped: PID $serverPid"
} else {
    Write-Output "Backend process $serverPid is not running."
}
Remove-Item -LiteralPath $pidFile -Force -ErrorAction SilentlyContinue

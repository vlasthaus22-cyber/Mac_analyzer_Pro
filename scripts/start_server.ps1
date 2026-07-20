param(
    [switch]$Background,
    [ValidateRange(1, 65535)]
    [int]$Port = 8080
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
$runtimeDirectory = Join-Path $root "data\runtime"
$pidFile = Join-Path $runtimeDirectory "server.pid"
$stdout = Join-Path $root "logs\server.stdout.log"
$stderr = Join-Path $root "logs\server.stderr.log"

function Test-BackendPort([int]$TargetPort) {
    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $connection = $client.BeginConnect("127.0.0.1", $TargetPort, $null, $null)
        return $connection.AsyncWaitHandle.WaitOne(250) -and $client.Connected
    } catch {
        return $false
    } finally {
        $client.Dispose()
    }
}

function Get-ListeningProcessId([int]$TargetPort) {
    $pattern = "127\.0\.0\.1:$TargetPort\s+.*LISTENING\s+(\d+)\s*$"
    foreach ($line in (netstat -ano -p tcp)) {
        if ($line -match $pattern) {
            return [int]$Matches[1]
        }
    }
    return $null
}

New-Item -ItemType Directory -Force -Path $runtimeDirectory, (Join-Path $root "logs") | Out-Null
$env:MAC_ANALYZER_PORT = [string]$Port

if ($Background) {
    if (Test-Path -LiteralPath $pidFile) {
        $recordedPid = [int](Get-Content -LiteralPath $pidFile -Raw).Trim()
        $recordedProcess = Get-Process -Id $recordedPid -ErrorAction SilentlyContinue
        if ($null -ne $recordedProcess) {
            try {
                $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 2
                if ($health.status -eq "ok") {
                    Write-Output "MAC Analyzer backend already running: PID $recordedPid, http://127.0.0.1:$Port/"
                    return
                }
            } catch {
                throw "PID $recordedPid is running, but the backend health check failed."
            }
        }
        Remove-Item -LiteralPath $pidFile -Force
    }
    if (Test-BackendPort $Port) {
        throw "Port $Port is already in use by another process. Stop it or choose another -Port."
    }

    # Windows may expose both Path and PATH; Start-Process rejects duplicate environment keys.
    $processPath = $env:Path
    [Environment]::SetEnvironmentVariable("PATH", $null, [EnvironmentVariableTarget]::Process)
    [Environment]::SetEnvironmentVariable("Path", $processPath, [EnvironmentVariableTarget]::Process)
    $process = Start-Process -FilePath $python -ArgumentList "server.py" -WorkingDirectory $root `
        -WindowStyle Hidden -RedirectStandardOutput $stdout -RedirectStandardError $stderr -PassThru
    for ($attempt = 0; $attempt -lt 50; $attempt++) {
        $process.Refresh()
        if ($process.HasExited) {
            $details = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Raw).Trim() } else { "" }
            throw "Backend exited before startup (code $($process.ExitCode)). $details"
        }
        try {
            $health = Invoke-RestMethod -Uri "http://127.0.0.1:$Port/api/health" -TimeoutSec 1
            if ($health.status -eq "ok") {
                $listenerPid = Get-ListeningProcessId $Port
                if ($null -eq $listenerPid) {
                    throw "Backend passed health check, but its listener PID was not found."
                }
                Set-Content -LiteralPath $pidFile -Value $listenerPid -Encoding ASCII
                Write-Output "MAC Analyzer backend started: PID $listenerPid, http://127.0.0.1:$Port/"
                return
            }
        } catch {
            Start-Sleep -Milliseconds 100
        }
    }
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "Backend did not pass /api/health within 5 seconds."
}

Write-Output "MAC Analyzer backend: http://127.0.0.1:$Port/"
Push-Location $root
try {
    & $python "server.py"
} finally {
    Pop-Location
}

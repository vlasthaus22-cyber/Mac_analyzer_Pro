param(
    [ValidateRange(1, 65535)]
    [int]$Port = 8080,
    [switch]$NoBrowser,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$root = (Split-Path -Parent $PSScriptRoot)
$runtimeDirectory = Join-Path $root "data\runtime"
$logDirectory = Join-Path $root "logs"
$pidFile = Join-Path $runtimeDirectory "server.pid"
$stdout = Join-Path $logDirectory "server.stdout.log"
$stderr = Join-Path $logDirectory "server.stderr.log"
$healthUrl = "http://127.0.0.1:$Port/api/health"
$appUrl = "http://127.0.0.1:$Port/"

function Test-MacAnalyzerHealth([int]$TargetPort) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$TargetPort/api/health" -TimeoutSec 1
        return $health.status -eq "ok"
    } catch {
        return $false
    }
}

function Test-PortAvailable([int]$TargetPort) {
    $listener = [System.Net.Sockets.TcpListener]::new([System.Net.IPAddress]::Loopback, $TargetPort)
    try {
        $listener.Start()
        return $true
    } catch {
        return $false
    } finally {
        try { $listener.Stop() } catch {}
    }
}

function Test-Python([string]$Executable, [string[]]$Prefix = @()) {
    try {
        & $Executable @Prefix -c "import sys; assert sys.version_info >= (3, 10)" 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Test-BackendDependencies([string]$Executable, [string[]]$Prefix = @()) {
    try {
        & $Executable @Prefix -c "import openpyxl, xlrd, PIL, reportlab" 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

if ($ValidateOnly) {
    [pscustomobject]@{
        root = $root
        server = Test-Path -LiteralPath (Join-Path $root "server.py")
        index = Test-Path -LiteralPath (Join-Path $root "index.html")
        requirements = Test-Path -LiteralPath (Join-Path $root "requirements-web.txt")
        portableExecutable = Test-Path -LiteralPath (Join-Path $root "MACAnalyzerBackend.exe")
    } | ConvertTo-Json -Compress
    exit 0
}

New-Item -ItemType Directory -Force -Path $runtimeDirectory, $logDirectory | Out-Null

if (Test-MacAnalyzerHealth $Port) {
    Write-Output "MAC Analyzer backend is already running: $appUrl"
    if (-not $NoBrowser) { Start-Process $appUrl }
    exit 0
}

if (-not (Test-PortAvailable $Port)) {
    $freePort = ($Port + 1)..([Math]::Min(65535, $Port + 20)) | Where-Object { Test-PortAvailable $_ } | Select-Object -First 1
    if (-not $freePort) { throw "No free local port was found near $Port." }
    $Port = $freePort
    $healthUrl = "http://127.0.0.1:$Port/api/health"
    $appUrl = "http://127.0.0.1:$Port/"
}

$portableExecutable = Join-Path $root "MACAnalyzerBackend.exe"
$filePath = ""
$argumentList = @()
$backendMode = ""
$pythonCandidates = @(
    (Join-Path $root ".venv-portable\Scripts\python.exe"),
    (Join-Path $root ".venv\Scripts\python.exe"),
    (Join-Path $root "runtime\python\python.exe")
)
$python = $pythonCandidates | Where-Object { (Test-Path -LiteralPath $_) -and (Test-Python $_) } | Select-Object -First 1
$pythonPrefix = @()

if (-not $python) {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher -and (Test-Python $pyLauncher.Source @("-3"))) {
        $python = $pyLauncher.Source
        $pythonPrefix = @("-3")
    }
}
if (-not $python) {
    $systemPython = Get-Command python -ErrorAction SilentlyContinue
    if ($systemPython -and (Test-Python $systemPython.Source)) { $python = $systemPython.Source }
}

if ($python) {
    if (-not (Test-BackendDependencies $python $pythonPrefix)) {
        $portableVenv = Join-Path $root ".venv-portable"
        Write-Output "Preparing a local Python environment without administrator rights..."
        & $python @pythonPrefix -m venv $portableVenv 2>> $stderr
        if ($LASTEXITCODE -eq 0) {
            $venvPython = Join-Path $portableVenv "Scripts\python.exe"
            & $venvPython -m pip install --disable-pip-version-check -r (Join-Path $root "requirements-web.txt") 2>> $stderr
            if ($LASTEXITCODE -eq 0 -and (Test-BackendDependencies $venvPython)) {
                $python = $venvPython
                $pythonPrefix = @()
            } else {
                $python = $null
            }
        } else {
            $python = $null
        }
    }
}

if ($python) {
    $filePath = $python
    $argumentList = @($pythonPrefix) + @("server.py")
    $backendMode = "Python source"
} elseif (Test-Path -LiteralPath $portableExecutable) {
    $filePath = $portableExecutable
    $backendMode = "built-in portable fallback"
} else {
    throw "No usable backend was found. Keep the complete universal package together or install Python 3.10+."
}

$env:MAC_ANALYZER_PORT = [string]$Port
$pathKeys = @([Environment]::GetEnvironmentVariables().Keys | Where-Object { [string]$_ -ieq "Path" })
if ($pathKeys.Count -gt 1) {
    $pathValue = $env:Path
    foreach ($pathKey in $pathKeys) {
        [Environment]::SetEnvironmentVariable([string]$pathKey, $null, "Process")
    }
    [Environment]::SetEnvironmentVariable("Path", $pathValue, "Process")
}
$startParameters = @{
    FilePath = $filePath
    WorkingDirectory = $root
    WindowStyle = "Hidden"
    RedirectStandardOutput = $stdout
    RedirectStandardError = $stderr
    PassThru = $true
}
if ($argumentList.Count) { $startParameters.ArgumentList = $argumentList }
Write-Output "Starting MAC Analyzer without elevation: $backendMode"
$process = Start-Process @startParameters

for ($attempt = 0; $attempt -lt 100; $attempt++) {
    $process.Refresh()
    if ($process.HasExited) {
        $details = if (Test-Path -LiteralPath $stderr) { (Get-Content -LiteralPath $stderr -Raw).Trim() } else { "" }
        throw "Backend exited during startup (code $($process.ExitCode)). $details"
    }
    if (Test-MacAnalyzerHealth $Port) {
        Set-Content -LiteralPath $pidFile -Value $process.Id -Encoding ASCII
        Write-Output "MAC Analyzer backend started: PID $($process.Id), $appUrl"
        if (-not $NoBrowser) { Start-Process $appUrl }
        exit 0
    }
    Start-Sleep -Milliseconds 100
}

Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
throw "Backend did not pass its health check within 10 seconds."

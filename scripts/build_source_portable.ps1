param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable" }
$package = Join-Path $outputRoot "source\MACAnalyzerWebSource"

if (Test-Path -LiteralPath $package) {
    Remove-Item -LiteralPath $package -Recurse -Force
}

$directories = @(
    "backend",
    "frontend",
    "config",
    "data\databases",
    "data\backups",
    "data\exports",
    "data\imports",
    "data\legacy",
    "data\reference",
    "data\runtime",
    "logs",
    "scripts"
)
foreach ($relativePath in $directories) {
    New-Item -ItemType Directory -Force -Path (Join-Path $package $relativePath) | Out-Null
}

$files = @(
    "index.html",
    "app.js",
    "styles.css",
    "server.py",
    "requirements-web.txt",
    "PARITY_REGISTRY.md",
    "PARITY_STATUS.json",
    "README_WEB.md",
    "PROJECT_STRUCTURE.md",
    "START_MAC_ANALYZER.cmd",
    "STOP_MAC_ANALYZER.cmd",
    "scripts\portable_launcher.py",
    "scripts\portable_start.ps1",
    "scripts\portable_stop.ps1"
)
foreach ($relativePath in $files) {
    Copy-Item -LiteralPath (Join-Path $root $relativePath) -Destination (Join-Path $package $relativePath) -Force
}

Copy-Item -Path (Join-Path $root "backend\*") -Destination (Join-Path $package "backend") -Recurse -Force
Copy-Item -Path (Join-Path $root "frontend\*") -Destination (Join-Path $package "frontend") -Recurse -Force
Get-ChildItem -LiteralPath $package -Directory -Filter "__pycache__" -Recurse -ErrorAction SilentlyContinue |
    Sort-Object { $_.FullName.Length } -Descending |
    Remove-Item -Recurse -Force
Get-ChildItem -LiteralPath $package -File -Include "*.pyc", "*.pyo" -Recurse -ErrorAction SilentlyContinue |
    Remove-Item -Force
foreach ($reference in (Get-ChildItem -LiteralPath (Join-Path $root "data\reference") -File -ErrorAction SilentlyContinue)) {
    Copy-Item -LiteralPath $reference.FullName -Destination (Join-Path $package "data\reference") -Force
}
$paritySource = Get-ChildItem -LiteralPath $root -Filter "MAC_ANALYZER *.py" -File | Select-Object -First 1
if ($paritySource) {
    Copy-Item -LiteralPath $paritySource.FullName -Destination $package -Force
}

[ordered]@{
    package = "MAC Analyzer Pro source backend"
    executableBackend = $false
    entryPoint = "server.py"
    launcher = "START_MAC_ANALYZER.cmd"
    requiresPython = "3.10+"
    dataDirectory = "data"
    database = "data/databases/mac_analyzer_web.db"
} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Encoding UTF8

$executables = @(Get-ChildItem -LiteralPath $package -Filter "*.exe" -File -Recurse -ErrorAction SilentlyContinue)
if ($executables.Count) {
    throw "Source package must not contain executable files: $($executables.FullName -join ', ')"
}

Write-Output "Source-only portable package created: $package"

param(
    [string]$OutputDirectory = "",
    [switch]$SkipClean
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) { throw "Create .venv and install requirements-web.txt before building." }
& $python -c "import PyInstaller, openpyxl, xlrd, PIL, reportlab"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller or backend dependencies are missing." }

$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable" }
$distPath = Join-Path $outputRoot "dist"
$workPath = Join-Path $root "data\build\pyinstaller"
$specPath = Join-Path $workPath "spec"
New-Item -ItemType Directory -Force -Path $outputRoot, $workPath, $specPath | Out-Null
if (-not $SkipClean -and (Test-Path -LiteralPath $distPath)) { Remove-Item -LiteralPath $distPath -Recurse -Force }

$data = @(
    @("index.html", "."),
    @("app.js", "."),
    @("styles.css", "."),
    @("mac_analyzer_standalone.html", "."),
    @("frontend", "frontend"),
    @("backend", "backend"),
    @("server.py", "."),
    @("PARITY_REGISTRY.md", "."),
    @("PARITY_STATUS.json", "."),
    @("README_WEB.md", "."),
    @("PROJECT_STRUCTURE.md", "."),
    @("scripts\portable_start.ps1", "scripts"),
    @("scripts\portable_stop.ps1", "scripts"),
    @("requirements-web.txt", ".")
)
$arguments = @(
    "-m", "PyInstaller", "--noconfirm", "--clean", "--onedir", "--contents-directory", ".",
    "--name", "MACAnalyzerBackend", "--distpath", $distPath, "--workpath", $workPath,
    "--specpath", $specPath, "--collect-all", "openpyxl", "--collect-all", "reportlab",
    "--collect-all", "PIL", "--hidden-import", "xlrd"
)
foreach ($item in $data) {
    $source = Join-Path $root $item[0]
    if (-not (Test-Path -LiteralPath $source)) { throw "Portable package input is missing: $source" }
    $arguments += @("--add-data", "$source;$($item[1])")
}
$paritySource = Get-ChildItem -LiteralPath $root -Filter "MAC_ANALYZER *.py" -File | Select-Object -First 1
if ($paritySource) { $arguments += @("--add-data", "$($paritySource.FullName);.") }
foreach ($reference in (Get-ChildItem -LiteralPath (Join-Path $root "data\reference") -File -ErrorAction SilentlyContinue)) {
    $arguments += @("--add-data", "$($reference.FullName);data\reference")
}
$arguments += Join-Path $root "server.py"

& $python @arguments
if ($LASTEXITCODE -ne 0) { throw "Portable backend build failed." }

$package = Join-Path $distPath "MACAnalyzerBackend"
Copy-Item -LiteralPath (Join-Path $root "START_MAC_ANALYZER.cmd") -Destination $package -Force
Copy-Item -LiteralPath (Join-Path $root "STOP_MAC_ANALYZER.cmd") -Destination $package -Force
Write-Output "Portable package created: $package"

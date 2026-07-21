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
$manifestPath = Join-Path $root "config\windows-as-invoker.manifest"
New-Item -ItemType Directory -Force -Path $outputRoot, $workPath, $specPath | Out-Null
if (-not $SkipClean -and (Test-Path -LiteralPath $distPath)) { Remove-Item -LiteralPath $distPath -Recurse -Force }
if (-not $SkipClean -and (Test-Path -LiteralPath (Join-Path $outputRoot "source"))) {
    Remove-Item -LiteralPath (Join-Path $outputRoot "source") -Recurse -Force
}
if (-not (Test-Path -LiteralPath $manifestPath)) { throw "Windows asInvoker manifest is missing: $manifestPath" }

$data = @(
    @("index.html", "."),
    @("app.js", "."),
    @("styles.css", "."),
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
    "--specpath", $specPath, "--manifest", $manifestPath, "--collect-all", "openpyxl", "--collect-all", "reportlab",
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
$verifiedFrontendFiles = @(
    "index.html",
    "app.js",
    "styles.css",
    "frontend\memory-guard.js",
    "frontend\file-readers.js",
    "frontend\state-persistence.js",
    "frontend\browser-snapshot-store.js",
    "frontend\guide.js"
)
$checksums = [ordered]@{}
foreach ($relativePath in $verifiedFrontendFiles) {
    $sourcePath = Join-Path $root $relativePath
    $packagePath = Join-Path $package $relativePath
    $sourceHash = (Get-FileHash -LiteralPath $sourcePath -Algorithm SHA256).Hash
    $packageHash = (Get-FileHash -LiteralPath $packagePath -Algorithm SHA256).Hash
    if ($sourceHash -ne $packageHash) { throw "Portable frontend is stale: $relativePath" }
    $checksums[$relativePath.Replace("\", "/")] = $packageHash
}
$forbiddenGuardPattern = '(?m)\bconst\s+memoryGuard\b|\bmemoryGuard\.'
foreach ($relativePath in @("app.js", "frontend\file-readers.js")) {
    $content = Get-Content -LiteralPath (Join-Path $package $relativePath) -Raw -Encoding UTF8
    if ($content -cmatch $forbiddenGuardPattern) { throw "Portable frontend contains obsolete memoryGuard code: $relativePath" }
}
$indexContent = Get-Content -LiteralPath (Join-Path $package "index.html") -Raw -Encoding UTF8
$buildVersion = if ($indexContent -match 'name="application-build" content="([^"]+)"') { $Matches[1] } else { "unknown" }
$revision = "unknown"
$git = Get-Command git -ErrorAction SilentlyContinue
if ($git) {
    $candidateRevision = (& $git.Source -C $root rev-parse HEAD 2>$null)
    if ($LASTEXITCODE -eq 0 -and $candidateRevision) { $revision = $candidateRevision.Trim() }
}
[ordered]@{
    buildVersion = $buildVersion
    builtAt = [DateTime]::UtcNow.ToString("o")
    sourceRevision = $revision
    frontendChecksums = $checksums
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $package "BUILD_INFO.json") -Encoding UTF8
[ordered]@{
    package = "MAC Analyzer Pro Universal"
    launcher = "START_MAC_ANALYZER.cmd"
    administratorRightsRequired = $false
    preferredBackend = "server.py via an available user Python"
    fallbackBackend = "MACAnalyzerBackend.exe (asInvoker)"
    dataDirectory = "data"
} | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Encoding UTF8
Write-Output "Universal no-admin package created: $package"

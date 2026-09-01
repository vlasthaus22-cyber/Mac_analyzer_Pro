param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.53",
    [string]$PortablePackage = "",
    [switch]$SkipCleanDatabase
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\everything" }
$packageName = "MAC-Analyzer-$Version-Windows"
$stagingRoot = Join-Path $outputRoot ".everything-staging"
$package = Join-Path $stagingRoot $packageName
$archive = Join-Path $outputRoot "$packageName.zip"

function Copy-DirectoryContents([string]$Source, [string]$Destination) {
    if (-not (Test-Path -LiteralPath $Source -PathType Container)) {
        throw "Package directory is missing: $Source"
    }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    foreach ($item in (Get-ChildItem -LiteralPath $Source -Force)) {
        Copy-Item -LiteralPath $item.FullName -Destination $Destination -Recurse -Force
    }
}

if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Force -Path $package | Out-Null

try {
    $runtimePackage = if ($PortablePackage) {
        [IO.Path]::GetFullPath($PortablePackage)
    } else {
        $runtimeBuildRoot = Join-Path $stagingRoot "runtime-build"
        & (Join-Path $root "scripts\build_portable.ps1") -OutputDirectory $runtimeBuildRoot | Out-Null
        Join-Path $runtimeBuildRoot "dist\MACAnalyzerBackend"
    }
    foreach ($required in @("MACAnalyzerBackend.exe", "START_MAC_ANALYZER.cmd", "PACKAGE_INFO.json")) {
        if (-not (Test-Path -LiteralPath (Join-Path $runtimePackage $required) -PathType Leaf)) {
            throw "Windows portable runtime is incomplete: $required"
        }
    }

    $sourceBuildRoot = Join-Path $stagingRoot "source-build"
    & (Join-Path $root "scripts\build_full_project_release.ps1") -OutputDirectory $sourceBuildRoot -Version $Version | Out-Null
    $sourceArchive = Join-Path $sourceBuildRoot "MAC-Analyzer-$Version-Source.zip"
    $expandedSourceRoot = Join-Path $stagingRoot "expanded-source"
    Expand-Archive -LiteralPath $sourceArchive -DestinationPath $expandedSourceRoot
    $sourcePackage = Join-Path $expandedSourceRoot "MAC-Analyzer-$Version-Source"

    Copy-DirectoryContents $runtimePackage (Join-Path $package "Windows-Portable")
    Copy-DirectoryContents $sourcePackage (Join-Path $package "Source")
    Copy-Item -LiteralPath (Join-Path $sourcePackage "MAC-Analyzer-Pro.html") -Destination (Join-Path $package "MAC-Analyzer-Pro.html") -Force

    $databaseReport = $null
    if (-not $SkipCleanDatabase) {
        $python = Join-Path $root ".venv\Scripts\python.exe"
        if (-not (Test-Path -LiteralPath $python -PathType Leaf)) {
            throw "Python environment is required to create the clean release database."
        }
        $windowsPackage = Join-Path $package "Windows-Portable"
        $databaseOutput = & $python (Join-Path $root "tools\create_clean_release_database.py") `
            --application-root $windowsPackage --data-root (Join-Path $windowsPackage "data")
        if ($LASTEXITCODE -ne 0) { throw "Clean release database creation failed." }
        $databaseReport = $databaseOutput | ConvertFrom-Json
    }
    $windowsPackage = Join-Path $package "Windows-Portable"
    $generatedCaches = @(
        Get-ChildItem -LiteralPath $windowsPackage -Recurse -Force |
            Where-Object { $_.Name -eq "__pycache__" -or $_.Extension -in @(".pyc", ".pyo") }
    )
    if ($generatedCaches.Count) {
        throw "Windows portable package contains generated Python caches: $($generatedCaches.FullName -join ', ')"
    }

    @(
        "MAC ANALYZER PRO - EVERYTHING PACKAGE"
        ""
        "1. No installation or Python: open MAC-Analyzer-Pro.html in a Chromium browser."
        "2. Ready Windows version with backend: open Windows-Portable and run START_MAC_ANALYZER.cmd."
        "3. Complete source code, tests, and tools: open Source."
        ""
        "A clean initialized SQLite database and the OUI reference are included."
        "User history, imports, exports, logs, secrets, and caches are not included."
    ) | Set-Content -LiteralPath (Join-Path $package "README_FIRST.txt") -Encoding UTF8

    $sourceInfo = Get-Content -LiteralPath (Join-Path $sourcePackage "PACKAGE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $runtimeFiles = @(Get-ChildItem -LiteralPath (Join-Path $package "Windows-Portable") -Recurse -File -Force)
    [ordered]@{
        package = "MAC Analyzer Pro everything package for Windows"
        version = $Version
        autonomousEntryPoint = "MAC-Analyzer-Pro.html"
        windowsLauncher = "Windows-Portable/START_MAC_ANALYZER.cmd"
        windowsBackend = "Windows-Portable/MACAnalyzerBackend.exe"
        sourceDirectory = "Source"
        trackedProjectFiles = $sourceInfo.trackedProjectFiles
        windowsRuntimeFiles = $runtimeFiles.Count
        administratorRightsRequired = $false
        cleanDatabaseIncluded = -not $SkipCleanDatabase
        cleanDatabase = if ($databaseReport) { "Windows-Portable/data/databases/mac_analyzer_web.db" } else { $null }
        cleanDatabaseIntegrity = if ($databaseReport) { $databaseReport.integrity } else { $null }
        cleanDatabaseTables = if ($databaseReport) { $databaseReport.tables } else { 0 }
        userRuntimeDataIncluded = $false
        runtimeDataPolicy = "A clean initialized database is included; user history, imports, exports, logs, secrets, and caches are excluded."
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Encoding UTF8

    $programFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File -Force)
    $packagePrefix = [IO.Path]::GetFullPath($package).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $manifestLines = foreach ($file in ($programFiles | Sort-Object FullName)) {
        $relative = [IO.Path]::GetFullPath($file.FullName).Substring($packagePrefix.Length).Replace("\", "/")
        "{0}  {1}" -f (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash, $relative
    }
    $manifestLines | Set-Content -LiteralPath (Join-Path $package "FILE_MANIFEST.sha256") -Encoding UTF8

    $finalFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File -Force)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression
    $archiveStream = [IO.File]::Open($archive, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        foreach ($file in ($finalFiles | Sort-Object FullName)) {
            $relative = [IO.Path]::GetFullPath($file.FullName).Substring($packagePrefix.Length).Replace("\", "/")
            $entry = $zip.CreateEntry("$packageName/$relative", [IO.Compression.CompressionLevel]::Optimal)
            $entryStream = $entry.Open()
            $sourceStream = $file.OpenRead()
            try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose(); $entryStream.Dispose() }
        }
    } finally {
        $zip.Dispose()
        $archiveStream.Dispose()
    }

    [pscustomobject]@{
        file = $archive
        bytes = (Get-Item -LiteralPath $archive).Length
        sha256 = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
        files = $finalFiles.Count
        trackedProjectFiles = $sourceInfo.trackedProjectFiles
        windowsRuntimeFiles = $runtimeFiles.Count
        autonomousHtmlIncluded = $true
        fullSourceIncluded = $true
        windowsRuntimeIncluded = $true
        cleanDatabaseIncluded = -not $SkipCleanDatabase
        cleanDatabaseBytes = if ($databaseReport) { $databaseReport.bytes } else { 0 }
        cleanDatabaseIntegrity = if ($databaseReport) { $databaseReport.integrity } else { "skipped" }
        cleanDatabaseTables = if ($databaseReport) { $databaseReport.tables } else { 0 }
        cleanDatabaseUserRows = if ($databaseReport) { $databaseReport.userDataRows } else { 0 }
        userRuntimeDataIncluded = $false
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}

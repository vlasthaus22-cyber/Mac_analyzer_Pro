param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.47",
    [string]$LegacyArchive = "",
    [string]$PortablePackage = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\legacy-data" }
$legacySource = if ($LegacyArchive) { [IO.Path]::GetFullPath($LegacyArchive) } else { Join-Path $root "portable\complete\MAC-Analyzer-Pro-v1.0.27-Complete.zip" }
$packageName = "MAC-Analyzer-$Version-Full"
$stagingRoot = Join-Path ([IO.Path]::GetTempPath()) ("mac-v1027-release-" + [Guid]::NewGuid().ToString("N"))
$package = Join-Path $stagingRoot $packageName
$archive = Join-Path $outputRoot "$packageName.zip"

if (-not (Test-Path -LiteralPath $legacySource -PathType Leaf)) { throw "v1.0.27 archive is missing: $legacySource" }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Force -Path $outputRoot, $stagingRoot | Out-Null

try {
    $baseOutput = Join-Path $stagingRoot "base"
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "scripts\build_everything_release.ps1"),
        "-OutputDirectory", $baseOutput,
        "-Version", $Version,
        "-SkipCleanDatabase"
    )
    if ($PortablePackage) { $arguments += @("-PortablePackage", [IO.Path]::GetFullPath($PortablePackage)) }
    & powershell @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Current Everything package build failed." }

    $baseArchive = Join-Path $baseOutput "MAC-Analyzer-$Version-Windows.zip"
    $expanded = Join-Path $stagingRoot "expanded"
    Expand-Archive -LiteralPath $baseArchive -DestinationPath $expanded
    $basePackage = Join-Path $expanded "MAC-Analyzer-$Version-Windows"
    Move-Item -LiteralPath $basePackage -Destination $package

    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python environment is required." }
    $prepareOutput = & $python (Join-Path $root "tools\prepare_legacy_release_data.py") `
        --legacy-archive $legacySource --package-root (Join-Path $package "Windows-Portable")
    if ($LASTEXITCODE -ne 0) { throw "v1.0.27 data preparation failed." }
    $legacyReport = $prepareOutput | ConvertFrom-Json

    @(
        ""
        "V1.0.27 DATA COMPATIBILITY"
        "This package contains the preserved v1.0.27 working database, history, snapshots, mappings, imports, backups, and logs."
        "The program code, Windows runtime, autonomous HTML, tests, and tools are the current improved version."
        "Saved API keys, passwords, webhooks, tokens, and engineering sessions are removed from the release copy."
    ) | Add-Content -LiteralPath (Join-Path $package "README_FIRST.txt") -Encoding UTF8

    $baseInfo = Get-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $sourceInfo = Get-Content -LiteralPath (Join-Path $package "Source\PACKAGE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    [ordered]@{
        package = "MAC Analyzer Pro current program with preserved v1.0.27 data"
        version = $Version
        gitCommit = $sourceInfo.gitCommit
        autonomousEntryPoint = "MAC-Analyzer-Pro.html"
        windowsLauncher = "Windows-Portable/START_MAC_ANALYZER.cmd"
        windowsBackend = "Windows-Portable/MACAnalyzerBackend.exe"
        sourceDirectory = "Source"
        trackedProjectFiles = $sourceInfo.trackedProjectFiles
        legacyDataSource = "MAC-Analyzer-Pro-v1.0.27-Complete.zip"
        legacyDatabaseIncluded = $true
        databaseIntegrity = $legacyReport.databaseIntegrity
        databaseTables = $legacyReport.databaseTables
        macHistoryRecords = $legacyReport.mac_history
        vendorModelHistoryRecords = $legacyReport.vendor_model_history
        snapshots = $legacyReport.snapshots
        vendorMappings = $legacyReport.vendor_mappings
        modelMappings = $legacyReport.model_mappings
        secretsRedacted = [int]$legacyReport.configSecretsRedacted + [int]$legacyReport.databaseSecretsRedacted
        engineeringSessionsRemoved = $legacyReport.engineeringSessionsRemoved
        administratorRightsRequired = $false
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Encoding UTF8

    if (Test-Path -LiteralPath (Join-Path $package "FILE_MANIFEST.sha256")) {
        Remove-Item -LiteralPath (Join-Path $package "FILE_MANIFEST.sha256") -Force
    }
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
        legacyDatabaseIncluded = $true
        databaseBytes = $legacyReport.databaseBytes
        databaseIntegrity = $legacyReport.databaseIntegrity
        macHistoryRecords = $legacyReport.mac_history
        vendorModelHistoryRecords = $legacyReport.vendor_model_history
        secretsRedacted = [int]$legacyReport.configSecretsRedacted + [int]$legacyReport.databaseSecretsRedacted
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}

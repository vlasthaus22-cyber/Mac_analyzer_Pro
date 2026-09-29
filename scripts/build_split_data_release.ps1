param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.78",
    [string]$LegacyArchive = "",
    [string]$PortablePackage = "",
    [int]$MinimumHistoryRecords = 500000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\split-data" }
$legacySource = if ($LegacyArchive) { [IO.Path]::GetFullPath($LegacyArchive) } else { Join-Path $root "portable\complete\MAC-Analyzer-Pro-v1.0.27-Complete.zip" }
$stagingRoot = Join-Path ([IO.Path]::GetTempPath()) ("mac-split-release-" + [Guid]::NewGuid().ToString("N"))
$programArchive = Join-Path $outputRoot "MAC-Analyzer-$Version-Full-Program.zip"
$databaseArchive = Join-Path $outputRoot "MAC-Analyzer-$Version-History-Database.zip"
$databasePackageName = "MAC-Analyzer-$Version-History-Database"

if (-not (Test-Path -LiteralPath $legacySource -PathType Leaf)) { throw "Historical archive is missing: $legacySource" }
New-Item -ItemType Directory -Force -Path $outputRoot, $stagingRoot | Out-Null
foreach ($target in @($programArchive, $databaseArchive)) {
    if (Test-Path -LiteralPath $target) { Remove-Item -LiteralPath $target -Force }
}

try {
    $baseOutput = Join-Path $stagingRoot "program"
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "scripts\build_everything_release.ps1"),
        "-OutputDirectory", $baseOutput,
        "-Version", $Version
    )
    if ($PortablePackage) { $arguments += @("-PortablePackage", [IO.Path]::GetFullPath($PortablePackage)) }
    & powershell @arguments | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Full program package build failed." }
    $builtProgram = Join-Path $baseOutput "MAC-Analyzer-$Version-Full-Clean.zip"
    if (-not (Test-Path -LiteralPath $builtProgram -PathType Leaf)) { throw "Program archive was not created: $builtProgram" }
    Move-Item -LiteralPath $builtProgram -Destination $programArchive

    # Prepare the historical database against the exact Windows runtime that
    # was already validated and packaged above.  Reusing this package avoids a
    # second ad-hoc backend copy and guarantees that imports/schema migrations
    # are identical to the released application.
    $expandedProgram = Join-Path $stagingRoot "expanded-program"
    Expand-Archive -LiteralPath $programArchive -DestinationPath $expandedProgram
    $prepareRoot = Join-Path $expandedProgram "MAC-Analyzer-$Version-Full-Clean\Windows-Portable"
    if (-not (Test-Path -LiteralPath (Join-Path $prepareRoot "server.py") -PathType Leaf)) {
        throw "Packaged Windows runtime is missing server.py."
    }
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $python -PathType Leaf)) { throw "Python environment is required." }
    $prepareOutput = & $python (Join-Path $root "tools\prepare_legacy_release_data.py") `
        --legacy-archive $legacySource `
        --package-root $prepareRoot `
        --minimum-history-records $MinimumHistoryRecords
    if ($LASTEXITCODE -ne 0) { throw "Historical database preparation failed." }
    $databaseReport = $prepareOutput | ConvertFrom-Json
    # Do not round-trip the Unicode temporary path through JSON/console
    # encoding.  The preparation utility has a stable, documented output path.
    $preparedDatabase = Join-Path $prepareRoot "data\backups\legacy-v1.0.27\mac_analyzer_web.db"
    if (-not (Test-Path -LiteralPath $preparedDatabase -PathType Leaf)) { throw "Prepared historical database is missing." }

    $databasePackage = Join-Path $stagingRoot $databasePackageName
    New-Item -ItemType Directory -Force -Path $databasePackage | Out-Null
    $databaseName = "mac_analyzer_history.db"
    $databaseTarget = Join-Path $databasePackage $databaseName
    Copy-Item -LiteralPath $preparedDatabase -Destination $databaseTarget
    @(
        "MAC ANALYZER PRO - HISTORICAL DATABASE"
        ""
        "This archive is optional. The full program works without it and creates a clean current database."
        "The file contains the preserved MAC, model and device history from v1.0.27."
        ""
        "IMPORT:"
        "1. Extract mac_analyzer_history.db from this archive."
        "2. Start the Full-Program package through START_HERE.cmd."
        "3. Enter engineering mode and open Data."
        "4. Click Load SQLite database and select mac_analyzer_history.db."
        "5. The import is additive: existing data is not deleted."
        ""
        "Autonomous browser-only HTML cannot open SQLite directly; use the included Windows/Python backend for this import."
    ) | Set-Content -LiteralPath (Join-Path $databasePackage "README_IMPORT.txt") -Encoding UTF8
    [ordered]@{
        package = "MAC Analyzer Pro historical database"
        version = $Version
        database = $databaseName
        databaseBytes = (Get-Item -LiteralPath $databaseTarget).Length
        databaseSha256 = (Get-FileHash -LiteralPath $databaseTarget -Algorithm SHA256).Hash
        integrity = $databaseReport.legacyDatabaseIntegrity
        tables = $databaseReport.legacyDatabaseTables
        macHistoryRecords = $databaseReport.mac_history
        vendorModelHistoryRecords = $databaseReport.vendor_model_history
        snapshots = $databaseReport.snapshots
        vendorMappings = $databaseReport.vendor_mappings
        modelMappings = $databaseReport.model_mappings
        secretsRedacted = [int]$databaseReport.configSecretsRedacted + [int]$databaseReport.databaseSecretsRedacted
        engineeringSessionsRemoved = $databaseReport.engineeringSessionsRemoved
        importMode = "additive"
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $databasePackage "DATABASE_INFO.json") -Encoding UTF8
    $databaseHash = (Get-FileHash -LiteralPath $databaseTarget -Algorithm SHA256).Hash
    "$databaseHash  $databaseName" | Set-Content -LiteralPath (Join-Path $databasePackage "FILE_MANIFEST.sha256") -Encoding UTF8

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression
    $databaseFiles = @(Get-ChildItem -LiteralPath $databasePackage -File -Force | Sort-Object Name)
    $archiveStream = [IO.File]::Open($databaseArchive, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        foreach ($file in $databaseFiles) {
            $entry = $zip.CreateEntry("$databasePackageName/$($file.Name)", [IO.Compression.CompressionLevel]::Optimal)
            $entryStream = $entry.Open()
            $sourceStream = $file.OpenRead()
            try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose(); $entryStream.Dispose() }
        }
    } finally {
        $zip.Dispose()
        $archiveStream.Dispose()
    }

    [pscustomobject]@{
        programFile = $programArchive
        programBytes = (Get-Item -LiteralPath $programArchive).Length
        programSha256 = (Get-FileHash -LiteralPath $programArchive -Algorithm SHA256).Hash
        databaseFile = $databaseArchive
        databaseArchiveBytes = (Get-Item -LiteralPath $databaseArchive).Length
        databaseArchiveSha256 = (Get-FileHash -LiteralPath $databaseArchive -Algorithm SHA256).Hash
        databaseBytes = (Get-Item -LiteralPath $databaseTarget).Length
        databaseIntegrity = $databaseReport.legacyDatabaseIntegrity
        macHistoryRecords = $databaseReport.mac_history
        vendorModelHistoryRecords = $databaseReport.vendor_model_history
        programContainsHistoricalDatabase = $false
        databaseIsSeparateAsset = $true
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}

param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.81",
    [string]$LegacyArchive = "",
    [string]$PortablePackage = "",
    [int]$MinimumHistoryRecords = 500000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\unified" }
$packageName = "MAC-Analyzer-$Version-Full"
$archive = Join-Path $outputRoot "$packageName.zip"
$temporaryRoot = Join-Path ([IO.Path]::GetTempPath()) ("mac-unified-release-" + [Guid]::NewGuid().ToString("N"))

New-Item -ItemType Directory -Force -Path $outputRoot, $temporaryRoot | Out-Null
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }

try {
    $splitOutput = Join-Path $temporaryRoot "split"
    $arguments = @(
        "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", (Join-Path $root "scripts\build_split_data_release.ps1"),
        "-OutputDirectory", $splitOutput,
        "-Version", $Version,
        "-MinimumHistoryRecords", $MinimumHistoryRecords
    )
    if ($LegacyArchive) { $arguments += @("-LegacyArchive", [IO.Path]::GetFullPath($LegacyArchive)) }
    if ($PortablePackage) { $arguments += @("-PortablePackage", [IO.Path]::GetFullPath($PortablePackage)) }
    $splitReportRaw = & powershell @arguments
    if ($LASTEXITCODE -ne 0) { throw "Program and historical database build failed." }
    $splitReport = $splitReportRaw | ConvertFrom-Json

    $programExpanded = Join-Path $temporaryRoot "program"
    $databaseExpanded = Join-Path $temporaryRoot "database"
    Expand-Archive -LiteralPath $splitReport.programFile -DestinationPath $programExpanded
    Expand-Archive -LiteralPath $splitReport.databaseFile -DestinationPath $databaseExpanded
    $programRoot = Get-ChildItem -LiteralPath $programExpanded -Directory | Select-Object -First 1
    $databaseRoot = Get-ChildItem -LiteralPath $databaseExpanded -Directory | Select-Object -First 1
    if (-not $programRoot -or -not $databaseRoot) { throw "Release packages have an invalid directory structure." }

    $package = Join-Path $temporaryRoot $packageName
    Move-Item -LiteralPath $programRoot.FullName -Destination $package
    $databaseSource = Join-Path $databaseRoot.FullName "mac_analyzer_history.db"
    $databaseInfoSource = Join-Path $databaseRoot.FullName "DATABASE_INFO.json"
    if (-not (Test-Path -LiteralPath $databaseSource -PathType Leaf)) { throw "Sanitized historical database is missing." }
    $databaseTargetDirectory = Join-Path $package "Windows-Portable\data\backups\legacy-v1.0.27"
    New-Item -ItemType Directory -Force -Path $databaseTargetDirectory | Out-Null
    Copy-Item -LiteralPath $databaseSource -Destination (Join-Path $databaseTargetDirectory "mac_analyzer_history.db") -Force
    Copy-Item -LiteralPath $databaseInfoSource -Destination (Join-Path $databaseTargetDirectory "DATABASE_INFO.json") -Force
    Copy-Item -LiteralPath (Join-Path $databaseRoot.FullName "README_IMPORT.txt") -Destination (Join-Path $package "HISTORY_DATABASE_README.txt") -Force

    $packageInfoPath = Join-Path $package "PACKAGE_INFO.json"
    $packageInfo = Get-Content -LiteralPath $packageInfoPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $packageInfo | Add-Member -NotePropertyName historicalDatabaseIncluded -NotePropertyValue $true -Force
    $packageInfo | Add-Member -NotePropertyName historicalDatabase -NotePropertyValue "Windows-Portable/data/backups/legacy-v1.0.27/mac_analyzer_history.db" -Force
    $packageInfo | Add-Member -NotePropertyName historicalDatabaseIntegrity -NotePropertyValue $splitReport.databaseIntegrity -Force
    $packageInfo | Add-Member -NotePropertyName historicalMacRecords -NotePropertyValue $splitReport.macHistoryRecords -Force
    $packageInfo | Add-Member -NotePropertyName historicalVendorModelRecords -NotePropertyValue $splitReport.vendorModelHistoryRecords -Force
    $packageInfo | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $packageInfoPath -Encoding UTF8

    Add-Content -LiteralPath (Join-Path $package "README_FIRST.txt") -Encoding UTF8 -Value @(
        ""
        "HISTORICAL DATABASE: the same archive includes the sanitized v1.0.27 MAC/model/history database."
        "Import instructions: HISTORY_DATABASE_README.txt. No passwords, tokens, sessions or imported source workbooks are included."
    )

    $manifestPath = Join-Path $package "FILE_MANIFEST.sha256"
    $packagePrefix = [IO.Path]::GetFullPath($package).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $manifestLines = foreach ($file in (Get-ChildItem -LiteralPath $package -Recurse -File -Force | Where-Object { $_.FullName -ne $manifestPath } | Sort-Object FullName)) {
        $relative = [IO.Path]::GetFullPath($file.FullName).Substring($packagePrefix.Length).Replace("\", "/")
        "{0}  {1}" -f (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash, $relative
    }
    $manifestLines | Set-Content -LiteralPath $manifestPath -Encoding UTF8

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
        fullProgramIncluded = $true
        fullSourceIncluded = $true
        windowsRuntimeIncluded = $true
        autonomousHtmlIncluded = $true
        cleanDatabaseIncluded = $true
        historicalDatabaseIncluded = $true
        historicalDatabaseBytes = (Get-Item -LiteralPath $databaseSource).Length
        databaseIntegrity = $splitReport.databaseIntegrity
        secretsRedacted = $true
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $temporaryRoot) { Remove-Item -LiteralPath $temporaryRoot -Recurse -Force }
}

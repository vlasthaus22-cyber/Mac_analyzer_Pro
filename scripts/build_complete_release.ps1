param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.7",
    [switch]$ExcludeRuntimeData
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\complete" }
$packageName = "MAC-Analyzer-Pro-$Version-Complete"
$stagingRoot = Join-Path $outputRoot ".complete-staging"
$package = Join-Path $stagingRoot $packageName
$archive = Join-Path $outputRoot "$packageName.zip"
$forbiddenExtensions = @(".exe", ".dll", ".com", ".msi", ".bat", ".cmd")

function Test-SkippedPath([string]$RelativePath) {
    $normalized = $RelativePath.Replace("\", "/")
    $segments = $normalized.Split("/")
    if ($segments -contains "__pycache__" -or $segments -contains ".git" -or $segments -contains ".venv" -or $segments -contains ".venv-portable") { return $true }
    if ($normalized -eq "mac_analyzer_standalone.html") { return $true }
    if ($normalized -match "(^|/)data/build(/|$)" -or $normalized -match "(^|/)data/runtime(/|$)" -or $normalized -match "(^|/)data/exports/releases(/|$)") { return $true }
    if ($normalized -match "(^|/)portable(/|$)") { return $true }
    return $forbiddenExtensions -contains [IO.Path]::GetExtension($normalized).ToLowerInvariant()
}

function Copy-ProjectFile([IO.FileInfo]$File, [string]$BasePath, [string]$DestinationRoot) {
    $baseFull = [IO.Path]::GetFullPath($BasePath).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    $fileFull = [IO.Path]::GetFullPath($File.FullName)
    if (-not $fileFull.StartsWith($baseFull, [StringComparison]::OrdinalIgnoreCase)) { throw "Source file is outside project root: $fileFull" }
    $relative = $fileFull.Substring($baseFull.Length)
    if (Test-SkippedPath $relative) { return }
    $destination = Join-Path $DestinationRoot $relative
    $parent = Split-Path -Parent $destination
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item -LiteralPath $File.FullName -Destination $destination -Force
}

if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Force -Path $package | Out-Null

try {
    foreach ($file in (Get-ChildItem -LiteralPath $root -File -Force)) {
        Copy-ProjectFile $file $root $package
    }
    foreach ($directory in @(".agents", "backend", "frontend", "scripts", "tests", "tools")) {
        $source = Join-Path $root $directory
        if (-not (Test-Path -LiteralPath $source)) { continue }
        foreach ($file in (Get-ChildItem -LiteralPath $source -Recurse -File -Force)) {
            Copy-ProjectFile $file $root $package
        }
    }

    $dataDirectories = @("data\databases", "data\backups", "data\imports", "data\legacy", "data\reference", "data\exports", "config", "logs")
    if (-not $ExcludeRuntimeData) {
        foreach ($directory in $dataDirectories) {
            $source = Join-Path $root $directory
            if (-not (Test-Path -LiteralPath $source)) { continue }
            foreach ($file in (Get-ChildItem -LiteralPath $source -Recurse -File -Force)) {
                Copy-ProjectFile $file $root $package
            }
        }
    } else {
        foreach ($directory in @("data\databases", "data\backups", "data\imports", "data\legacy", "data\reference", "data\exports", "config", "logs")) {
            New-Item -ItemType Directory -Force -Path (Join-Path $package $directory) | Out-Null
        }
    }
    if (Test-Path -LiteralPath (Join-Path $root "data\README.md")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $package "data") | Out-Null
        Copy-Item -LiteralPath (Join-Path $root "data\README.md") -Destination (Join-Path $package "data\README.md") -Force
    }

    $htmlBuild = Join-Path $stagingRoot "html"
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\build_html_portable.ps1") -OutputDirectory $htmlBuild | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Autonomous HTML build failed." }
    Copy-Item -LiteralPath (Join-Path $htmlBuild "MAC-Analyzer-Pro.html") -Destination (Join-Path $package "MAC-Analyzer-Pro.html") -Force

    $programFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File -Force)
    $forbidden = @($programFiles | Where-Object { $forbiddenExtensions -contains $_.Extension.ToLowerInvariant() })
    if ($forbidden.Count) { throw "Complete package contains forbidden executable or command files: $($forbidden.FullName -join ', ')" }

    [ordered]@{
        package = "MAC Analyzer Pro complete project"
        version = $Version
        autonomousEntryPoint = "MAC-Analyzer-Pro.html"
        pythonEntryPoint = "server.py"
        executableFiles = 0
        commandFiles = 0
        runtimeDataIncluded = -not $ExcludeRuntimeData
        dataDirectory = "data"
        database = "data/databases/mac_analyzer_web.db"
    } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $package "PACKAGE_INFO.json") -Encoding UTF8

    $programFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File -Force)
    $manifestLines = foreach ($file in ($programFiles | Sort-Object FullName)) {
        $packageFull = [IO.Path]::GetFullPath($package).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        $relative = [IO.Path]::GetFullPath($file.FullName).Substring($packageFull.Length).Replace("\", "/")
        "{0}  {1}" -f (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash, $relative
    }
    $manifestLines | Set-Content -LiteralPath (Join-Path $package "FILE_MANIFEST.sha256") -Encoding UTF8

    $finalFiles = @(Get-ChildItem -LiteralPath $package -Recurse -File -Force)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.IO.Compression
    $archiveStream = [IO.File]::Open($archive, [IO.FileMode]::CreateNew, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    $zip = [IO.Compression.ZipArchive]::new($archiveStream, [IO.Compression.ZipArchiveMode]::Create, $false)
    try {
        $packageFull = [IO.Path]::GetFullPath($package).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
        foreach ($file in ($finalFiles | Sort-Object FullName)) {
            $relative = [IO.Path]::GetFullPath($file.FullName).Substring($packageFull.Length).Replace("\", "/")
            $entry = $zip.CreateEntry("$packageName/$relative", [IO.Compression.CompressionLevel]::Optimal)
            $entryStream = $entry.Open()
            $sourceStream = $file.OpenRead()
            try { $sourceStream.CopyTo($entryStream) } finally { $sourceStream.Dispose(); $entryStream.Dispose() }
        }
    } finally {
        $zip.Dispose()
        $archiveStream.Dispose()
    }
    $archiveHash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash
    [pscustomobject]@{
        file = $archive
        bytes = (Get-Item -LiteralPath $archive).Length
        sha256 = $archiveHash
        files = $finalFiles.Count
        sourceFiles = @($finalFiles | Where-Object { $_.FullName -notmatch "[\\/]data[\\/]" -and $_.FullName -notmatch "[\\/]config[\\/]" -and $_.FullName -notmatch "[\\/]logs[\\/]" }).Count
        dataFiles = @($finalFiles | Where-Object { $_.FullName -match "[\\/](data|config|logs)[\\/]" }).Count
        executableFiles = 0
        commandFiles = 0
        runtimeDataIncluded = -not $ExcludeRuntimeData
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}

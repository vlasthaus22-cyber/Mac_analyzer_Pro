param(
    [string]$OutputDirectory = "",
    [string]$Version = "v1.0.62"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\full-project" }
$packageName = "MAC-Analyzer-$Version-Source"
$stagingRoot = Join-Path $outputRoot ".full-project-staging"
$package = Join-Path $stagingRoot $packageName
$archive = Join-Path $outputRoot "$packageName.zip"

function Get-TrackedProjectFiles {
    $git = Get-Command git.exe -ErrorAction Stop
    $startInfo = [Diagnostics.ProcessStartInfo]::new()
    $startInfo.FileName = $git.Source
    $startInfo.Arguments = "-C `"$root`" -c core.quotepath=false ls-files -z"
    $startInfo.UseShellExecute = $false
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $startInfo.StandardOutputEncoding = [Text.UTF8Encoding]::new($false)
    $startInfo.StandardErrorEncoding = [Text.UTF8Encoding]::new($false)
    $process = [Diagnostics.Process]::new()
    $process.StartInfo = $startInfo
    if (-not $process.Start()) { throw "Unable to start git." }
    $output = $process.StandardOutput.ReadToEnd()
    $errorOutput = $process.StandardError.ReadToEnd()
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw "git ls-files failed: $errorOutput" }
    return @($output.Split([char[]]@([char]0), [StringSplitOptions]::RemoveEmptyEntries))
}

function Copy-TrackedProjectFile([string]$RelativePath) {
    $normalized = $RelativePath.Replace("/", [IO.Path]::DirectorySeparatorChar)
    $source = [IO.Path]::GetFullPath((Join-Path $root $normalized))
    $rootPrefix = [IO.Path]::GetFullPath($root).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $source.StartsWith($rootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Tracked path is outside the project root: $RelativePath"
    }
    if (-not (Test-Path -LiteralPath $source -PathType Leaf)) {
        throw "Tracked project file is missing from the working tree: $RelativePath"
    }
    $destination = Join-Path $package $normalized
    $parent = Split-Path -Parent $destination
    if ($parent) { New-Item -ItemType Directory -Force -Path $parent | Out-Null }
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
if (Test-Path -LiteralPath $archive) { Remove-Item -LiteralPath $archive -Force }
New-Item -ItemType Directory -Force -Path $package | Out-Null

try {
    $trackedFiles = @(Get-TrackedProjectFiles)
    if (-not $trackedFiles.Count) { throw "Git returned no tracked project files." }
    foreach ($relativePath in $trackedFiles) {
        Copy-TrackedProjectFile $relativePath
    }

    $htmlBuild = Join-Path $stagingRoot "html"
    & (Join-Path $root "scripts\build_html_portable.ps1") -OutputDirectory $htmlBuild | Out-Null
    Copy-Item -LiteralPath (Join-Path $htmlBuild "MAC-Analyzer-Pro.html") -Destination (Join-Path $package "MAC-Analyzer-Pro.html") -Force

    $commit = (& (Get-Command git.exe -ErrorAction Stop).Source -C $root rev-parse HEAD).Trim()
    if ($LASTEXITCODE -ne 0) { throw "Unable to resolve the Git commit." }
    [ordered]@{
        package = "MAC Analyzer Pro full project"
        version = $Version
        gitCommit = $commit
        trackedProjectFiles = $trackedFiles.Count
        fullTrackedProject = $true
        autonomousEntryPoint = "MAC-Analyzer-Pro.html"
        browserSourceEntryPoint = "index.html"
        pythonEntryPoint = "server.py"
        optionalWindowsLauncher = "START_MAC_ANALYZER.cmd"
        runtimeDataIncluded = $false
        runtimeDataPolicy = "User databases, imports, exports, logs, secrets, caches, and build output are excluded by Git."
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
        trackedProjectFiles = $trackedFiles.Count
        generatedFiles = $finalFiles.Count - $trackedFiles.Count
        fullTrackedProject = $true
        runtimeDataIncluded = $false
    } | ConvertTo-Json -Compress
} finally {
    if (Test-Path -LiteralPath $stagingRoot) { Remove-Item -LiteralPath $stagingRoot -Recurse -Force }
}

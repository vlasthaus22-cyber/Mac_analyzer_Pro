param(
    [string]$OutputDirectory = ""
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$outputRoot = if ($OutputDirectory) { [IO.Path]::GetFullPath($OutputDirectory) } else { Join-Path $root "portable\html" }
$outputFile = Join-Path $outputRoot "MAC-Analyzer-Pro.html"

if (Test-Path -LiteralPath $outputRoot) {
    $resolvedOutput = [IO.Path]::GetFullPath($outputRoot)
    $resolvedPortable = [IO.Path]::GetFullPath((Join-Path $root "portable")).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if (-not $OutputDirectory -and -not $resolvedOutput.StartsWith($resolvedPortable, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to clean an output directory outside portable/."
    }
    Remove-Item -LiteralPath $outputRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null

$html = Get-Content -LiteralPath (Join-Path $root "index.html") -Raw -Encoding UTF8
$styles = Get-Content -LiteralPath (Join-Path $root "styles.css") -Raw -Encoding UTF8
$stylePattern = '<link\s+rel="stylesheet"\s+href="styles\.css\?v=[^"]+"\s*>'
$html = [regex]::Replace($html, $stylePattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) "<style>`n$styles`n</style>" }, 1)

$scripts = @(
    "frontend/memory-guard.js",
    "frontend/file-readers.js",
    "frontend/state-persistence.js",
    "frontend/browser-snapshot-store.js",
    "frontend/mac-chronology.js",
    "frontend/xlsx-exporter.js",
    "frontend/full-xlsx-report.js",
    "frontend/portable-database.js",
    "frontend/local-folder-store.js",
    "frontend/workspace-file-lifecycle.js",
    "frontend/guide.js",
    "app.js"
)
foreach ($relativePath in $scripts) {
    $source = Join-Path $root $relativePath.Replace("/", "\")
    if (-not (Test-Path -LiteralPath $source)) { throw "HTML module is missing: $relativePath" }
    $content = Get-Content -LiteralPath $source -Raw -Encoding UTF8
    if ($content -match '</script') { throw "HTML module contains a closing script tag: $relativePath" }
    $escapedPath = [regex]::Escape($relativePath)
    $pattern = "<script\s+src=`"$escapedPath\?v=[^`"]+`"\s*></script>"
    $replacement = "<script data-inline-source=`"$relativePath`">`n$content`n</script>"
    $html = [regex]::Replace($html, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{ param($match) $replacement }, 1)
}

# The source page keeps a last-resort inline controller for partial deployments.
# The complete one-file build already embeds app.js, so retaining that controller
# would make the browser parse a second copy of the application.
$fallbackPattern = '(?s)\s*<script>\s*window\.addEventListener\("DOMContentLoaded", \(\) => \{\s*if \(window\.MacAnalyzerAppBootstrapped.*?</script>\s*(?=</body>)'
$html = [regex]::Replace($html, $fallbackPattern, "`n", 1)

$html = [regex]::Replace(
    $html,
    '<meta name="application-build" content="([^"]+)">',
    '<meta name="application-build" content="$1-html">',
    1
)
Set-Content -LiteralPath $outputFile -Value $html -Encoding UTF8

$built = Get-Content -LiteralPath $outputFile -Raw -Encoding UTF8
if ($built -match '<script\s+src=' -or $built -match '<link\s+rel="stylesheet"') {
    throw "Autonomous HTML still contains external code dependencies."
}
foreach ($marker in @(
    "window.MacAnalyzerAppBootstrapped = true;",
    "window.MacAnalyzerPortableDatabase",
    "window.MacAnalyzerXlsxExporter",
    "window.MacAnalyzerFullXlsxReport",
    "window.MacAnalyzerLocalFolderStore",
    "window.MacAnalyzerWorkspaceFileLifecycle",
    "xlsxWorksheetRows",
    "assertEnrichmentCapacity",
    "id=`"portableDatabaseButton`""
)) {
    if (-not $built.Contains($marker)) { throw "Autonomous HTML marker is missing: $marker" }
}
if ($built.Contains("window.MacAnalyzerFallbackReady = true;")) {
    throw "Autonomous HTML still contains the duplicate fallback controller."
}
$unexpected = @(Get-ChildItem -LiteralPath $outputRoot -File | Where-Object { $_.Extension -ne ".html" })
if ($unexpected.Count) { throw "Autonomous package contains non-HTML files: $($unexpected.Name -join ', ')" }

$hash = Get-FileHash -LiteralPath $outputFile -Algorithm SHA256
[pscustomobject]@{
    file = $outputFile
    bytes = (Get-Item -LiteralPath $outputFile).Length
    sha256 = $hash.Hash
    executableFiles = 0
    commandFiles = 0
    backendFiles = 0
} | ConvertTo-Json -Compress

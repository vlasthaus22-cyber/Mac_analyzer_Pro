param(
    [string]$Filter = "test_*.py"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$testsRoot = Join-Path $root "tests"
$venvPython = Join-Path $root ".venv\Scripts\python.exe"
$python = if (Test-Path -LiteralPath $venvPython) { $venvPython } else { "python" }
$nodeCommand = Get-Command node -ErrorAction SilentlyContinue
$bundledNode = Join-Path $HOME ".cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe"
$nodeExecutable = if ($null -ne $nodeCommand) {
    $nodeCommand.Source
} elseif (Test-Path -LiteralPath $bundledNode) {
    $bundledNode
} else {
    $null
}
$files = @(Get-ChildItem -LiteralPath $testsRoot -Filter $Filter -File | Sort-Object Name)
$failed = [System.Collections.Generic.List[string]]::new()
$passed = 0
$testRuntimeRoot = Join-Path $root "data\runtime\tests"
$testDataDirectory = Join-Path $testRuntimeRoot ([Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $testDataDirectory | Out-Null

if (-not $files.Count) {
    throw "No tests matched $Filter"
}

$previousPythonPath = $env:PYTHONPATH
$previousDataDirectory = $env:MAC_ANALYZER_DATA_DIR
$previousDatabasePath = $env:MAC_ANALYZER_DATABASE_PATH
$env:PYTHONPATH = if ($previousPythonPath) { "$root;$previousPythonPath" } else { $root }
$env:MAC_ANALYZER_DATA_DIR = $testDataDirectory
$env:MAC_ANALYZER_DATABASE_PATH = Join-Path $testDataDirectory "databases\mac_analyzer_web.db"
Push-Location $root
try {
    foreach ($file in $files) {
        $module = "tests.$($file.BaseName)"
        & $python -m $module
        if ($LASTEXITCODE -eq 0) {
            $passed++
        } else {
            $failed.Add($file.Name)
        }
    }

    if ($null -ne $nodeExecutable) {
        $javascriptFiles = @((Get-Item -LiteralPath (Join-Path $root "app.js")))
        $javascriptFiles += Get-ChildItem -LiteralPath (Join-Path $root "frontend") -Filter "*.js" -File
        foreach ($javascriptFile in $javascriptFiles) {
            & $nodeExecutable --check $javascriptFile.FullName
            if ($LASTEXITCODE -ne 0) {
                $failed.Add("$($javascriptFile.Name) syntax")
            }
        }
        foreach ($javascriptTest in (Get-ChildItem -LiteralPath (Join-Path $root "tests") -Filter "*.test.js" -File)) {
            & $nodeExecutable $javascriptTest.FullName
            if ($LASTEXITCODE -ne 0) {
                $failed.Add($javascriptTest.Name)
            }
        }
    }
} finally {
    Pop-Location
    $env:PYTHONPATH = $previousPythonPath
    $env:MAC_ANALYZER_DATA_DIR = $previousDataDirectory
    $env:MAC_ANALYZER_DATABASE_PATH = $previousDatabasePath
    $resolvedTestData = [IO.Path]::GetFullPath($testDataDirectory)
    $resolvedTestRoot = [IO.Path]::GetFullPath($testRuntimeRoot).TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar
    if ($resolvedTestData.StartsWith($resolvedTestRoot, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $resolvedTestData)) {
        Remove-Item -LiteralPath $resolvedTestData -Recurse -Force
    }
}

$testFunctions = (Select-String -Path $files.FullName -Pattern "^def test_" | Measure-Object).Count
Write-Output "Test files: $passed/$($files.Count); test functions: $testFunctions"
if ($failed.Count) {
    Write-Output "Failed: $($failed -join ', ')"
    exit 1
}
Write-Output "All project checks passed."

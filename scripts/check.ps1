# Run lint and tests from the repository root.
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $python = Join-Path $root ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Virtual environment not found at $python. Create it first (see README.md)."
    }

    & $python -m ruff check app tests
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

    & $python -m pytest
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

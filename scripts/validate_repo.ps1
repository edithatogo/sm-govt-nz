param(
    [ValidateSet("quick", "workflows", "full")]
    [string]$Scope = "quick"
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$dev = Join-Path $repoRoot "scripts/dev.ps1"

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host "==> $Name"
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Set-Location $repoRoot

if ($Scope -in @("quick", "full")) {
    Invoke-Step "Ruff" { & $dev --with ruff ruff check --no-cache src tests scripts }
}

if ($Scope -in @("workflows", "full")) {
    $actionlint = Get-Command actionlint -ErrorAction SilentlyContinue
    if ($actionlint) {
        Invoke-Step "Actionlint" { & $actionlint.Source }
    }
    else {
        Write-Warning "actionlint is not installed locally; CI enforces workflow linting."
    }

    Invoke-Step "Workflow contract tests" {
        & $dev --with pytest python -m pytest `
            tests/test_govt_source_discovery_workflow.py `
            tests/test_archive_registered_sources_workflow.py `
            tests/test_threads_workflow_reporting.py `
            tests/test_repo_management.py `
            tests/test_publish_archives_workflow.py `
            -q
    }
}

if ($Scope -eq "quick") {
    Invoke-Step "Tests" { & $dev --with pytest python -m pytest tests -q }
}
elseif ($Scope -eq "full") {
    Invoke-Step "Tests" { & $dev --with pytest python -m pytest tests -q }
}

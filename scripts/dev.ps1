param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$uv = Get-Command uv -ErrorAction Stop

if (-not $Args -or $Args.Count -eq 0) {
    Write-Host "Usage: .\scripts\dev.ps1 <command> [args...]"
    Write-Host "Example: .\scripts\dev.ps1 pytest tests/test_govt_source_discovery.py"
    exit 1
}

& $uv.Source run --python 3.14 @Args
exit $LASTEXITCODE

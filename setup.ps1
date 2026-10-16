param([string]$Python = '')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if ($Python) {
    & $Python scripts/setup_local.py
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3.12 scripts/setup_local.py
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python scripts/setup_local.py
} else {
    throw 'Install Python 3.12, then reopen PowerShell. See README.md.'
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

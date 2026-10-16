param([ValidateRange(0, 65535)][int]$Port = 0)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$voiceScopePython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $voiceScopePython)) {
    Write-Host 'Run .\setup.ps1 first, or use Docker Compose. See README.md.'
    exit 1
}
$voiceScopeArguments = @('-m', 'backend.run')
if ($Port -gt 0) { $voiceScopeArguments += @('--port', [string]$Port) }
& $voiceScopePython @voiceScopeArguments
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

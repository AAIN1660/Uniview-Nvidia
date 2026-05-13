# Load unified.env automatically, then start NAT from .venv_nat (same args as `nat`).
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$python = Join-Path $PSScriptRoot ".venv_nat\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw ".venv_nat not found. Create it and install NAT dependencies, then retry."
}

& $python (Join-Path $PSScriptRoot "run_nat_serve.py") @args

# Start MinIO on Windows without Docker.
# Usage (from Backend/):
#   powershell -ExecutionPolicy Bypass -File .\scripts\start-minio-windows.ps1
#
# API:     http://localhost:9000
# Console: http://localhost:9001  (minioadmin / minioadmin)

$ErrorActionPreference = "Stop"
$BackendRoot = Split-Path $PSScriptRoot -Parent
$ToolsDir = Join-Path $BackendRoot "tools\minio"
$Exe = Join-Path $ToolsDir "minio.exe"
$DataDir = Join-Path $BackendRoot "minio-data"
$MinioUrl = "https://dl.min.io/server/minio/release/windows-amd64/minio.exe"
# Official release is ~108 MiB; smaller files are incomplete/corrupt downloads.
$MinExpectedBytes = 100000000

function Test-MinioExecutable {
    param([string]$Path)
    if (-not (Test-Path $Path)) { return $false }
    if ((Get-Item $Path).Length -lt $MinExpectedBytes) { return $false }
    try {
        $out = & $Path --version 2>&1
        return ($LASTEXITCODE -eq 0 -or ($out -match "minio"))
    } catch {
        return $false
    }
}

if (-not (Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Path $ToolsDir -Force | Out-Null
}

if (-not (Test-MinioExecutable $Exe)) {
    if (Test-Path $Exe) {
        Write-Host "Removing invalid or incomplete minio.exe (re-downloading)..."
        Remove-Item $Exe -Force
    }
    Write-Host "Downloading MinIO server for Windows (~108 MB, may take a few minutes)..."
    $tmp = Join-Path $env:TEMP ("minio-download-{0}.exe" -f [guid]::NewGuid().ToString("N"))
    try {
        Invoke-WebRequest -Uri $MinioUrl -OutFile $tmp -UseBasicParsing
        if ((Get-Item $tmp).Length -lt $MinExpectedBytes) {
            throw "Download too small ($((Get-Item $tmp).Length) bytes). Check network/proxy and retry."
        }
        Move-Item -Path $tmp -Destination $Exe -Force
        Unblock-File -Path $Exe -ErrorAction SilentlyContinue
    } finally {
        if (Test-Path $tmp) { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    }
    if (-not (Test-MinioExecutable $Exe)) {
        throw "minio.exe failed validation after download. Delete tools\minio\minio.exe and run this script again."
    }
    Write-Host "Download complete: $((Get-Item $Exe).Length) bytes"
}

if (-not (Test-Path $DataDir)) {
    New-Item -ItemType Directory -Path $DataDir -Force | Out-Null
}

$env:MINIO_ROOT_USER = "minioadmin"
$env:MINIO_ROOT_PASSWORD = "minioadmin"

Write-Host "Starting MinIO..."
Write-Host "  API:     http://localhost:9000"
Write-Host "  Console: http://localhost:9001"
Write-Host "  Data:    $DataDir"
Write-Host "Press Ctrl+C to stop."
Write-Host ""

Set-Location $BackendRoot
& $Exe server $DataDir --console-address ":9001"

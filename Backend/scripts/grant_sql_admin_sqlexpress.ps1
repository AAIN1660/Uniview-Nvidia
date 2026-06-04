# Run this file as Administrator (right-click PowerShell -> Run as administrator):
#   Set-ExecutionPolicy Bypass -Scope Process -Force
#   cd D:\AICOE\Uniview-Nvidia\Backend\scripts
#   .\grant_sql_admin_sqlexpress.ps1

$ErrorActionPreference = 'Stop'
$Service = 'MSSQL$SQLEXPRESS'
$Instance = 'localhost\SQLEXPRESS'
$SaPassword = 'Abcdchildhood@123'

Write-Host "=== Close ALL SSMS windows before continuing ===" -ForegroundColor Yellow
Start-Sleep -Seconds 3

Write-Host "Stopping SQL Agent (if running)..."
Stop-Service -Name 'SQLAgent$SQLEXPRESS' -Force -ErrorAction SilentlyContinue

Write-Host "Stopping $Service ..."
net stop $Service | Out-Null

Write-Host "Starting $Service in single-user mode (sqlcmd only)..."
# /mSQLCMD = only sqlcmd.exe may connect (critical)
net start $Service /mSQLCMD | Out-Null

Start-Sleep -Seconds 2

$sql = @"
ALTER LOGIN [sa] ENABLE;
ALTER LOGIN [sa] WITH PASSWORD = '$SaPassword', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
"@

Write-Host "Resetting sa password on $Instance ..."
& sqlcmd -S $Instance -E -Q $sql
if ($LASTEXITCODE -ne 0) {
    Write-Host "sa reset failed; trying CREATE unified_app ..." -ForegroundColor Yellow
    $sql2 = @"
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'unified_app')
    CREATE LOGIN [unified_app] WITH PASSWORD = '$SaPassword', CHECK_POLICY = OFF, CHECK_EXPIRATION = OFF;
ALTER SERVER ROLE [sysadmin] ADD MEMBER [unified_app];
"@
    & sqlcmd -S $Instance -E -Q $sql2
}

Write-Host "Returning SQL to normal mode..."
net stop $Service | Out-Null
net start $Service | Out-Null

Write-Host "Done. Test in SSMS: SQL auth -> $Instance -> sa / password above" -ForegroundColor Green
Write-Host "Then: CREATE DATABASE unified;  and  python test_sql.py" -ForegroundColor Green

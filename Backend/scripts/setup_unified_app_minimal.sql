-- Run ONLY after diagnose_sql_permissions.sql shows IsSysAdmin = 1
-- OR after your Windows login was added to sysadmin (see README steps below)
-- Creates unified_app + access to unified database (no sa required)

USE master;
GO

IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'unified_app')
BEGIN
    CREATE LOGIN [unified_app]
    WITH PASSWORD = 'Abcdchildhood@123',
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF,
         DEFAULT_DATABASE = [master];
    PRINT 'Created login unified_app.';
END
ELSE
BEGIN
    ALTER LOGIN [unified_app] ENABLE;
    ALTER LOGIN [unified_app]
    WITH PASSWORD = 'Abcdchildhood@123',
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF;
    PRINT 'Updated login unified_app.';
END
GO

USE [unified];
GO

IF NOT EXISTS (SELECT 1 FROM sys.database_principals WHERE name = 'unified_app')
BEGIN
    CREATE USER [unified_app] FOR LOGIN [unified_app];
END
GO

ALTER ROLE [db_owner] ADD MEMBER [unified_app];
GO

PRINT 'OK. Set in unified.env: SQL_USERNAME=unified_app  (same password as above)';
GO

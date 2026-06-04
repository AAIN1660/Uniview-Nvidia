-- Use this ONLY if the sa script still fails (permission / sa issues).
-- Creates a dedicated login instead of sa. Then set in unified.env:
--   SQL_USERNAME = unified_app
--   SQL_PASSWORD = (same password as below)

USE master;
GO

IF EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'unified_app')
    DROP LOGIN [unified_app];
GO

CREATE LOGIN [unified_app]
WITH PASSWORD = 'Abcdchildhood@123',
     CHECK_POLICY = OFF,
     CHECK_EXPIRATION = OFF,
     DEFAULT_DATABASE = [master];
GO

ALTER SERVER ROLE [sysadmin] ADD MEMBER [unified_app];
GO

PRINT 'Created unified_app. Update SQL_USERNAME=unified_app in unified.env';
GO

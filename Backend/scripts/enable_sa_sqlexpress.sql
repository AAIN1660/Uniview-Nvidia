-- Run in SSMS: connect to localhost\SQLEXPRESS with Windows Authentication
-- Run SSMS "as Administrator" if you get permission errors.
-- Change the password in BOTH places below if yours differs from unified.env

USE master;
GO

-- 1) Create sa if missing (common on SQL Express)
IF NOT EXISTS (SELECT 1 FROM sys.server_principals WHERE name = 'sa')
BEGIN
    CREATE LOGIN [sa]
    WITH PASSWORD = 'Abcdchildhood@123',
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF,
         DEFAULT_DATABASE = [master];
    PRINT 'Created login sa.';
END
ELSE
BEGIN
    ALTER LOGIN [sa] ENABLE;
    ALTER LOGIN [sa]
    WITH PASSWORD = 'Abcdchildhood@123',
         CHECK_POLICY = OFF,
         CHECK_EXPIRATION = OFF;
    PRINT 'Updated login sa.';
END
GO

-- 2) Allow sa to administer the server (needed for the app)
ALTER SERVER ROLE [sysadmin] ADD MEMBER [sa];
GO

PRINT 'Done. Test: SQL auth to localhost\SQLEXPRESS as sa.';
GO

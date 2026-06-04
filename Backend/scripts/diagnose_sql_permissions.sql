-- Run in SSMS connected to localhost\SQLEXPRESS (Windows Authentication)
-- Shows whether YOU have enough rights to create/fix logins

SELECT
    SUSER_SNAME() AS [YourLogin],
    IS_SRVROLEMEMBER('sysadmin') AS [IsSysAdmin_1Yes_0No],
    IS_SRVROLEMEMBER('securityadmin') AS [IsSecurityAdmin];

SELECT name, type_desc, is_disabled, create_date
FROM sys.server_principals
WHERE name IN ('sa', 'unified_app', SUSER_SNAME());

SELECT name, state_desc FROM sys.databases WHERE name = 'unified';

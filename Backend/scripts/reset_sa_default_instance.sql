-- Run in SSMS connected to: localhost  (DEFAULT instance, NOT \SQLEXPRESS)
-- You should have IsSysAdmin = 1 on this instance (diagnose on "localhost")

USE master;
GO

ALTER LOGIN [sa] ENABLE;
ALTER LOGIN [sa]
WITH PASSWORD = 'Abcdchildhood@123',
     CHECK_POLICY = OFF,
     CHECK_EXPIRATION = OFF;
GO

PRINT 'sa password set on DEFAULT instance. unified database already exists here.';
GO

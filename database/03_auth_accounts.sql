-- Apply explicitly to the EXISTING ProfRates_databaza after taking a backup.
-- No database creation, deletes, resets or changes to rating calculations.
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
IF DB_NAME() <> N'ProfRates_databaza' THROW 51000, 'Select ProfRates_databaza first.', 1;
IF OBJECT_ID(N'dbo.Users',N'U') IS NULL OR OBJECT_ID(N'dbo.Admins',N'U') IS NULL
 OR OBJECT_ID(N'dbo.PasswordResets',N'U') IS NULL OR OBJECT_ID(N'dbo.ActivityLogs',N'U') IS NULL
 THROW 51001, 'Required original tables missing. Stop and inspect the schema.', 1;
IF EXISTS (SELECT LOWER(LTRIM(RTRIM(Email))) FROM dbo.Users GROUP BY LOWER(LTRIM(RTRIM(Email))) HAVING COUNT(*)>1)
 OR EXISTS (SELECT LOWER(LTRIM(RTRIM(Email))) FROM dbo.Admins GROUP BY LOWER(LTRIM(RTRIM(Email))) HAVING COUNT(*)>1)
 THROW 51002, 'Case-insensitive duplicate emails found. Resolve manually; no rows changed.', 1;
BEGIN TRY
 BEGIN TRANSACTION;
 IF COL_LENGTH('dbo.PasswordResets','Code') < 64
  ALTER TABLE dbo.PasswordResets ALTER COLUMN Code varchar(64) NOT NULL;
 ALTER TABLE dbo.PasswordResets ALTER COLUMN UserID int NULL;
 IF COL_LENGTH('dbo.PasswordResets','AdminID') IS NULL
  ALTER TABLE dbo.PasswordResets ADD AdminID int NULL;
 IF COL_LENGTH('dbo.PasswordResets','Purpose') IS NULL
  ALTER TABLE dbo.PasswordResets ADD Purpose varchar(10) NOT NULL CONSTRAINT DF_PasswordResets_Purpose DEFAULT('legacy') WITH VALUES;
 IF NOT EXISTS (SELECT 1 FROM sys.foreign_keys WHERE name='FK_PasswordResets_Admins')
  ALTER TABLE dbo.PasswordResets WITH CHECK ADD CONSTRAINT FK_PasswordResets_Admins FOREIGN KEY(AdminID) REFERENCES dbo.Admins(AdminID);
 IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_PasswordResets_Account')
  EXEC(N'ALTER TABLE dbo.PasswordResets WITH CHECK ADD CONSTRAINT CK_PasswordResets_Account CHECK
   ((UserID IS NOT NULL AND AdminID IS NULL) OR (UserID IS NULL AND AdminID IS NOT NULL));');
 IF NOT EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_PasswordResets_Purpose')
  EXEC(N'ALTER TABLE dbo.PasswordResets WITH CHECK ADD CONSTRAINT CK_PasswordResets_Purpose CHECK (Purpose IN (''reset'',''verify'',''legacy''));');
 IF COL_LENGTH('dbo.Admins','IsEmailVerified') IS NULL
  ALTER TABLE dbo.Admins ADD IsEmailVerified bit NOT NULL CONSTRAINT DF_Admins_EmailVerified DEFAULT(0) WITH VALUES;
 -- Retain the existing audit table; anonymous/system events have both actors NULL.
 IF EXISTS (SELECT 1 FROM sys.check_constraints WHERE name='CK_ActivityLogs_Actor')
  ALTER TABLE dbo.ActivityLogs DROP CONSTRAINT CK_ActivityLogs_Actor;
 ALTER TABLE dbo.ActivityLogs WITH CHECK ADD CONSTRAINT CK_ActivityLogs_Actor
  CHECK (UserID IS NULL OR AdminID IS NULL);
 IF OBJECT_ID('dbo.AuthSessions','U') IS NULL
  CREATE TABLE dbo.AuthSessions (
   SessionHash varchar(64) NOT NULL CONSTRAINT PK_AuthSessions PRIMARY KEY,
   UserID int NULL, AdminID int NULL, CSRFHash varchar(64) NOT NULL,
   CreatedAt datetime NOT NULL, ExpiresAt datetime NOT NULL,
   CONSTRAINT FK_AuthSessions_User FOREIGN KEY(UserID) REFERENCES dbo.Users(UserID),
   CONSTRAINT FK_AuthSessions_Admin FOREIGN KEY(AdminID) REFERENCES dbo.Admins(AdminID),
   CONSTRAINT CK_AuthSessions_Actor CHECK ((UserID IS NOT NULL AND AdminID IS NULL) OR (UserID IS NULL AND AdminID IS NOT NULL))
  );
 IF OBJECT_ID('dbo.AuthRateLimits','U') IS NULL
  CREATE TABLE dbo.AuthRateLimits (
   KeyHash varchar(64) NOT NULL CONSTRAINT PK_AuthRateLimits PRIMARY KEY,
   WindowStart int NOT NULL, Attempts int NOT NULL
  );
 IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.AuthSessions') AND name='IX_AuthSessions_User')
  CREATE INDEX IX_AuthSessions_User ON dbo.AuthSessions(UserID);
 IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.AuthSessions') AND name='IX_AuthSessions_Admin')
  CREATE INDEX IX_AuthSessions_Admin ON dbo.AuthSessions(AdminID);
 COMMIT;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK;
 THROW;
END CATCH;

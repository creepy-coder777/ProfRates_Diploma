-- Select the existing ProfRates database in SSMS first.
-- Read-only evidence only. No RESTORE DATABASE, CREATE, DROP or ALTER.
SELECT DB_NAME() AS CurrentDatabase, @@VERSION AS SqlServerVersion;
SELECT name, create_date, compatibility_level, collation_name
FROM sys.databases WHERE database_id=DB_ID();

-- Optional: requires permission to read msdb backup/restore history.
SELECT TOP (10) rh.restore_date, rh.destination_database_name, rh.restore_type,
       bs.database_name AS BackupDatabaseName, bs.backup_start_date, bs.backup_finish_date,
       bs.backup_set_uuid, bs.first_lsn, bs.last_lsn, bs.database_backup_lsn
FROM msdb.dbo.restorehistory AS rh
JOIN msdb.dbo.backupset AS bs ON bs.backup_set_id=rh.backup_set_id
WHERE rh.destination_database_name=DB_NAME()
ORDER BY rh.restore_date DESC;

-- Replace this with a backup path accessible to the SQL Server service, then run ONLY if permitted.
-- This reads the backup header; it does not restore a database.
-- RESTORE HEADERONLY FROM DISK = N'C:\YourBackupFolder\ProfRates_database_21.10.26 (2).bak';

-- Database names, dates and GUID/LSN history alone do not prove that the schema has not changed.

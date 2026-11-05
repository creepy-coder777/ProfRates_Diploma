USE [ProfRates_databaza];
GO
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;

BEGIN TRY
    BEGIN TRANSACTION;

    IF EXISTS (
        SELECT LOWER(LTRIM(RTRIM(Email)))
        FROM dbo.Users
        GROUP BY LOWER(LTRIM(RTRIM(Email)))
        HAVING COUNT(*) > 1
    )
        THROW 51040, N'Կրկնվող էլփոստ կա։ Նախ պետք է ճշտել տվյալները։', 1;

    IF OBJECT_ID('dbo.StudentRoster', 'U') IS NULL
        CREATE TABLE dbo.StudentRoster (
            Email nvarchar(255) NOT NULL
                CONSTRAINT PK_StudentRoster PRIMARY KEY,
            FirstName nvarchar(100) NOT NULL,
            LastName nvarchar(100) NOT NULL,
            GroupID int NOT NULL,
            IsActive bit NOT NULL
                CONSTRAINT DF_StudentRoster_IsActive DEFAULT (1),
            UserID int NULL,
            CONSTRAINT FK_StudentRoster_Group
                FOREIGN KEY (GroupID) REFERENCES dbo.StudentGroups(GroupID),
            CONSTRAINT FK_StudentRoster_User
                FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
        );

    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE object_id = OBJECT_ID('dbo.StudentRoster')
          AND name = 'UX_StudentRoster_User'
    )
        CREATE UNIQUE INDEX UX_StudentRoster_User
        ON dbo.StudentRoster(UserID)
        WHERE UserID IS NOT NULL;

    -- Existing coursework records are the initial trusted list by user request.
    -- Existing accounts remain linked; no account/password/verification is changed.
    EXEC(N'
        INSERT INTO dbo.StudentRoster
            (Email, FirstName, LastName, GroupID, IsActive, UserID)
        SELECT LOWER(LTRIM(RTRIM(u.Email))),
               u.FirstName, u.LastName, u.GroupID,
               CASE WHEN u.Status = ''Active'' THEN 1 ELSE 0 END,
               u.UserID
        FROM dbo.Users u
        WHERE u.GroupID IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM dbo.StudentRoster r
              WHERE r.Email = LOWER(LTRIM(RTRIM(u.Email)))
                 OR r.UserID = u.UserID
          );
    ');

    COMMIT TRANSACTION;

    SELECT N'Թույլատրված ցանկը ստեղծված է։ Հին հաշիվները պահպանված են։'
        AS [Արդյունք];
    EXEC(N'SELECT COUNT(*) AS [Ցանկի ուսանողներ] FROM dbo.StudentRoster;');
    SELECT COUNT(*) AS [Առանց խմբի՝ ցանկ չտեղափոխված հաշիվներ]
    FROM dbo.Users WHERE GroupID IS NULL;
END TRY
BEGIN CATCH
    IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;

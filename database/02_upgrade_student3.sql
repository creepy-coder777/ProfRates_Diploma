-- Existing database only. No DROP, no reset, no reseeding. Run once or re-run safely.
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
IF DB_NAME() <> N'ProfRates_databaza' THROW 51000, 'Select ProfRates_databaza first.', 1;
BEGIN TRY
 BEGIN TRANSACTION;
IF OBJECT_ID(N'dbo.RatingReactions', N'U') IS NULL
 CREATE TABLE dbo.RatingReactions (
  RatingID int NOT NULL, UserID int NOT NULL, Reaction smallint NOT NULL,
  CONSTRAINT PK_RatingReactions PRIMARY KEY (RatingID,UserID),
  CONSTRAINT CK_RatingReactions_Value CHECK (Reaction IN (-1,1)),
  CONSTRAINT FK_RatingReactions_Rating FOREIGN KEY (RatingID) REFERENCES dbo.Ratings(RatingID) ON DELETE CASCADE,
  CONSTRAINT FK_RatingReactions_User FOREIGN KEY (UserID) REFERENCES dbo.Users(UserID)
 );
 EXEC(N'CREATE OR ALTER TRIGGER dbo.tr_RatingReactions_Counters ON dbo.RatingReactions
AFTER INSERT, UPDATE, DELETE AS
BEGIN
 SET NOCOUNT ON;
 IF EXISTS (SELECT 1 FROM inserted i JOIN dbo.Ratings r ON r.RatingID=i.RatingID
            WHERE r.Status <> ''Approved'' OR r.Comment IS NULL OR LTRIM(RTRIM(r.Comment))='''')
  THROW 51020, ''Only published comments accept reactions.'', 1;
 ;WITH delta AS (
  SELECT RatingID, SUM(LikeDelta) AS LikeDelta, SUM(DislikeDelta) AS DislikeDelta
  FROM (
   SELECT RatingID, CASE WHEN Reaction=1 THEN 1 ELSE 0 END AS LikeDelta,
          CASE WHEN Reaction=-1 THEN 1 ELSE 0 END AS DislikeDelta FROM inserted
   UNION ALL
   SELECT RatingID, CASE WHEN Reaction=1 THEN -1 ELSE 0 END,
          CASE WHEN Reaction=-1 THEN -1 ELSE 0 END FROM deleted
  ) changes GROUP BY RatingID
 )
 UPDATE r SET Likes=r.Likes+d.LikeDelta, Dislikes=r.Dislikes+d.DislikeDelta
 FROM dbo.Ratings r JOIN delta d ON d.RatingID=r.RatingID;
END;');
 EXEC(N'CREATE OR ALTER VIEW [dbo].[vwLecturerRatingSummary] AS
SELECT l.LecturerID,l.FirstName,l.MiddleName,l.LastName,
 COUNT(CASE WHEN r.OverallScore IS NOT NULL THEN 1 END) AS TotalRatings,
 COALESCE(SUM(r.TotalAnswers),0) AS TotalAnswers,
 CAST(AVG(r.OverallScore) AS decimal(5,2)) AS AverageScore
FROM dbo.Lecturers l LEFT JOIN dbo.vwRatingScores r ON r.LecturerID=l.LecturerID
GROUP BY l.LecturerID,l.FirstName,l.MiddleName,l.LastName;

');
 EXEC(N'CREATE OR ALTER VIEW [dbo].[vwLecturerTermRatingSummary]
AS
SELECT
    s.LecturerID,
    s.TermID,
    t.TermLabel,

    COUNT(*) AS TotalRatings,

    CAST(
        AVG(
            CONVERT(DECIMAL(12, 4), s.OverallScore)
        )
        AS DECIMAL(5, 2)
    ) AS AverageScore

FROM dbo.vwRatingScores s

LEFT JOIN dbo.vwAcademicTerms t
    ON t.TermID = s.TermID

WHERE
    s.OverallScore IS NOT NULL

GROUP BY
    s.LecturerID,
    s.TermID,
    t.TermLabel;
');
 COMMIT TRANSACTION;
END TRY
BEGIN CATCH
 IF @@TRANCOUNT>0 ROLLBACK TRANSACTION;
 THROW;
END CATCH;

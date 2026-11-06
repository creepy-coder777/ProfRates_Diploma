-- PREPARED ONLY: not applied by the application or startup scripts.
-- Review current definitions and make a database backup BEFORE operator approval.
-- No tables/data, Bayesian defaults, procedures, or triggers are changed.
-- Needed only if the existing summaries include Pending/Rejected ratings.
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
IF DB_NAME() <> N'ProfRates_databaza' THROW 51000, 'Select ProfRates_databaza first.', 1;
IF OBJECT_ID('dbo.vwRatingScores','V') IS NULL OR OBJECT_ID('dbo.vwAcademicTerms','V') IS NULL
 THROW 51001, 'Missing source views. Stop and inspect the database.', 1;
BEGIN TRY
 BEGIN TRANSACTION;
 EXEC(N'CREATE OR ALTER VIEW [dbo].[vwLecturerRatingSummary] AS
SELECT l.LecturerID,l.FirstName,l.MiddleName,l.LastName,
 COUNT(CASE WHEN r.OverallScore IS NOT NULL THEN 1 END) AS TotalRatings,
 COALESCE(SUM(r.TotalAnswers),0) AS TotalAnswers,
 CAST(AVG(r.OverallScore) AS decimal(5,2)) AS AverageScore
FROM dbo.Lecturers l LEFT JOIN dbo.vwRatingScores r ON r.LecturerID=l.LecturerID AND r.Status=''Approved''
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
    s.Status = ''Approved'' AND s.OverallScore IS NOT NULL

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

-- Read-only: inspect live definitions before considering the optional 05 script.
USE [ProfRates_databaza];
SELECT s.name AS SchemaName,o.name AS ObjectName,o.type_desc,m.definition
FROM sys.objects o
JOIN sys.schemas s ON s.schema_id=o.schema_id
LEFT JOIN sys.sql_modules m ON m.object_id=o.object_id
WHERE s.name=N'dbo' AND o.name IN
 (N'vwRatingScores',N'vwLecturerRatingSummary',N'vwLecturerTermRatingSummary',
  N'vw_Ratings_Public',N'uspLecturerRankings');
-- NULL definitions can indicate missing VIEW DEFINITION permissions.

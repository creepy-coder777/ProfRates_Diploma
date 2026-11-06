from datetime import datetime
import pytest
from sqlalchemy import create_engine,text
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from app.main import app
from app.security import Principal,get_current_user
from app.student2.dependencies import get_db
from app.student2.tables import TABLES as T
from app.auth import tables as auth_tables

@pytest.fixture
def database():
    engine=create_engine('sqlite://',poolclass=StaticPool,connect_args={'check_same_thread':False},execution_options={'schema_translate_map':{'dbo':None}})
    # Միայն թեստային հիշողության բազայում, երբեք production-ում։
    for table in T.values():table.create(engine)
    with engine.begin() as db:
        db.execute(T['Admins'].insert().values(AdminID=1,Email='test@example.test',PasswordHash='unused',FirstName='Ադմին'))
        db.execute(T['AcademicSemesters'].insert().values(SemesterNumber=1,NameHy='Առաջին'))
        db.execute(T['Users'].insert().values(UserID=1,FirstName='Ուսանող',LastName='Փորձ',Email='s@example.test',PasswordHash='unused',IsEmailVerified=True,Status='Active'))
        for sql in [
          "CREATE VIEW vwRatingScores AS SELECT r.RatingID,r.LecturerID,r.Status,AVG(a.Score*1.0) AS OverallScore,COUNT(a.AnswerID) AS TotalAnswers FROM Ratings r LEFT JOIN RatingAnswers a ON a.RatingID=r.RatingID GROUP BY r.RatingID,r.LecturerID,r.Status",
          "CREATE VIEW vwLecturerRatingSummary AS SELECT l.LecturerID,COUNT(CASE WHEN r.OverallScore IS NOT NULL THEN 1 END) AS TotalRatings,COALESCE(SUM(r.TotalAnswers),0) AS TotalAnswers,AVG(r.OverallScore) AS AverageScore FROM Lecturers l LEFT JOIN vwRatingScores r ON r.LecturerID=l.LecturerID AND r.Status='Approved' GROUP BY l.LecturerID",
          "CREATE VIEW vw_Ratings_Admin AS SELECT r.RatingID,r.LecturerID,l.FirstName AS LecturerName,u.FirstName AS StudentName,NULL AS StudentGroup,s.OverallScore,r.Comment,r.Status,r.CreatedAt FROM Ratings r JOIN Lecturers l ON l.LecturerID=r.LecturerID JOIN Users u ON u.UserID=r.UserID JOIN vwRatingScores s ON s.RatingID=r.RatingID",
          "CREATE VIEW vw_Ratings_Public AS SELECT r.RatingID,r.LecturerID,s.OverallScore,r.Comment,r.CreatedAt,r.Likes,r.Dislikes FROM Ratings r JOIN vwRatingScores s ON s.RatingID=r.RatingID WHERE r.Status='Approved'",
        ]:db.execute(text(sql))
    with engine.begin() as db:
        for sql in [
            "CREATE TRIGGER reaction_insert AFTER INSERT ON RatingReactions BEGIN UPDATE Ratings SET Likes=Likes+CASE WHEN NEW.Reaction=1 THEN 1 ELSE 0 END, Dislikes=Dislikes+CASE WHEN NEW.Reaction=-1 THEN 1 ELSE 0 END WHERE RatingID=NEW.RatingID; END",
            "CREATE TRIGGER reaction_delete AFTER DELETE ON RatingReactions BEGIN UPDATE Ratings SET Likes=Likes-CASE WHEN OLD.Reaction=1 THEN 1 ELSE 0 END, Dislikes=Dislikes-CASE WHEN OLD.Reaction=-1 THEN 1 ELSE 0 END WHERE RatingID=OLD.RatingID; END",
            "CREATE TRIGGER reaction_update AFTER UPDATE ON RatingReactions BEGIN UPDATE Ratings SET Likes=Likes-CASE WHEN OLD.Reaction=1 THEN 1 ELSE 0 END, Dislikes=Dislikes-CASE WHEN OLD.Reaction=-1 THEN 1 ELSE 0 END WHERE RatingID=OLD.RatingID; UPDATE Ratings SET Likes=Likes+CASE WHEN NEW.Reaction=1 THEN 1 ELSE 0 END, Dislikes=Dislikes+CASE WHEN NEW.Reaction=-1 THEN 1 ELSE 0 END WHERE RatingID=NEW.RatingID; END"
        ]:
            db.execute(text(sql))
    yield engine
    engine.dispose()

@pytest.fixture
def api(database):
    def connection():
        with database.begin() as db:yield db
    app.dependency_overrides[get_db]=connection
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,1)
    with TestClient(app) as client:yield client
    app.dependency_overrides.clear()

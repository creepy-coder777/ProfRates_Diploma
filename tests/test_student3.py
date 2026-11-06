from datetime import datetime, timedelta
import pytest
from sqlalchemy import select, func
from app.main import app
from app.security import Principal, get_current_user
from app.student2.tables import TABLES as T
from test_student2 import curriculum, question


@pytest.fixture
def student(api, database):
    c = curriculum(api)
    q = question(api)
    with database.begin() as db:
        term = db.execute(T['AcademicTerms'].insert().values(
            AcademicYearStart=2026, TermNumber=1, NameHy='test')).inserted_primary_key[0]
        db.execute(T['StudentAcademicProgress'].insert().values(
            UserID=1, TermID=term, SemesterNumber=1, IsCurrent=True))
        db.execute(T['StudentCourses'].insert().values(UserID=1, CourseID=c['courses'], EnrolledAt=datetime.now()))
    app.dependency_overrides[get_current_user] = lambda: Principal(1, False)
    payload = dict(LecturerID=c['lecturer'], CourseID=c['courses'], TermID=term,
                   Comment='idiot', answers=[dict(QuestionID=q, Score=5)])
    return api, database, payload


def create(student):
    api, db, payload = student
    result = api.post('/api/ratings', json=payload)
    assert result.status_code == 201, result.text
    return result.json()


def enable_edit(database, ident):
    with database.begin() as db:
        db.execute(T['Ratings'].update().where(T['Ratings'].c.RatingID == ident).values(
            EditExpiry=datetime.now() + timedelta(hours=1)))


def test_create_private_and_no_identity_spoofing(student):
    api, database, payload = student
    assert api.post('/api/ratings', json={**payload, 'UserID': 2}).status_code == 422
    record = create(student)
    assert record['Status'] == 'Pending'
    assert 'UserID' not in record and 'ApprovedByAdminID' not in record
    assert api.post('/api/ratings', json=payload).status_code == 409
    assert len(api.get('/api/me/ratings').json()['items']) == 1
    with database.connect() as db:
        assert db.execute(select(T['ActivityLogs'].c.UserID).where(
            T['ActivityLogs'].c.Target == f"Ratings:{record['RatingID']}" )).scalar_one() == 1


def test_reject_missing_or_wrong_answers_and_enrollment(student):
    api, database, payload = student
    assert api.post('/api/ratings', json={**payload, 'answers': []}).status_code == 422
    assert api.post('/api/ratings', json={**payload, 'answers': payload['answers'] * 2}).status_code == 422
    for value in (0, 6, True, '5'):
        assert api.post('/api/ratings', json={**payload, 'answers': [dict(QuestionID=payload['answers'][0]['QuestionID'], Score=value)]}).status_code == 422
    assert api.post('/api/ratings', json={**payload, 'answers': [dict(QuestionID=999, Score=5)]}).status_code == 409
    assert api.post('/api/ratings', json={**payload, 'CourseID': 999}).status_code == 403
    assert api.post('/api/ratings', json={**payload, 'TermID': 999}).status_code == 403
    with database.begin() as db:
        db.execute(T['StudentCourses'].delete())
    assert api.post('/api/ratings', json=payload).status_code == 403


def test_owner_expiry_version_and_history(student):
    api, database, payload = student
    record = create(student); ident = record['RatingID']
    body = {**payload, 'expected_updated_at': record['UpdatedAt']}
    with database.begin() as db:
        db.execute(T['Ratings'].update().where(T['Ratings'].c.RatingID == ident).values(EditExpiry=db.execute(select(func.current_timestamp())).scalar_one()-timedelta(hours=1)))
    assert api.put(f'/api/ratings/{ident}', json=body).status_code == 409
    enable_edit(database, ident)
    with database.begin() as db:
        db.execute(T['Ratings'].update().where(T['Ratings'].c.RatingID==ident).values(Status='Approved'))
        db.execute(T['Questions'].update().values(IsActive=False))
    changed={**body,'answers':[dict(QuestionID=body['answers'][0]['QuestionID'],Score=4)]}
    assert api.put(f'/api/ratings/{ident}',json=changed).status_code==409
    body['Comment']='Clear explanation'
    result = api.put(f'/api/ratings/{ident}', json=body)
    assert result.status_code == 200, result.text
    assert result.json()['answers'][0]['Score'] == 5
    assert api.get(f'/api/me/ratings/{ident}/questions').json()['items'][0]['IsActive'] is False
    stale = {**body, 'expected_updated_at': '2000-01-01T00:00:00'}
    assert api.put(f'/api/ratings/{ident}', json=stale).status_code == 409
    app.dependency_overrides[get_current_user] = lambda: Principal(None, True, 1)
    assert api.get(f'/api/me/ratings/{ident}').status_code == 403
    # Create a valid second student, but never allow ownership through a request body.
    with database.begin() as db:
        db.execute(T['Users'].insert().values(UserID=2, FirstName='other', LastName='student',
            Email='other@example.test', PasswordHash='unused', IsEmailVerified=True, Status='Active'))
    app.dependency_overrides[get_current_user] = lambda: Principal(2, False)
    assert api.get(f'/api/me/ratings/{ident}').status_code == 404
    assert api.get('/api/me/ratings/9999').status_code == 404
    assert api.put(f'/api/ratings/{ident}', json=body).status_code == 404
    assert api.delete(f'/api/ratings/{ident}', params={'expected_updated_at': record['UpdatedAt']}).status_code == 404


def test_moderation_anonymity_statistics_and_delete(student):
    api, database, payload = student
    record = create(student); ident = record['RatingID']; lecturer = payload['LecturerID']
    assert api.get(f'/api/lecturers/{lecturer}/ratings').json()['total'] == 0
    app.dependency_overrides[get_current_user] = lambda: Principal(None, True, 1)
    response = api.put(f'/api/admin/comments/{ident}/moderation', json={'status': 'Approved', 'expected_status': 'Pending'})
    assert response.status_code == 200, response.text
    public = api.get(f'/api/lecturers/{lecturer}/ratings').json()['items'][0]
    assert set(public) == {'RatingID', 'LecturerID', 'OverallScore', 'Comment', 'CreatedAt', 'Likes', 'Dislikes'}
    stats = api.get(f'/api/lecturers/{lecturer}/statistics').json()
    assert stats['AverageScore'] == 5 and stats['TotalRatings'] == 1
    assert stats['distribution'][-1] == {'score': 5, 'count': 1}
    assert api.get(f'/api/admin/lecturers/{lecturer}/rating-statistics').json()['comment_status_counts']['Approved'] == 1
    app.dependency_overrides[get_current_user] = lambda: Principal(1, False)
    enable_edit(database, ident)
    latest = api.get(f'/api/me/ratings/{ident}').json()
    result = api.put(f'/api/ratings/{ident}', json={**payload, 'Comment': 'idiot edited', 'expected_updated_at': latest['UpdatedAt']})
    assert result.status_code == 200
    assert result.json()['Status'] == 'Pending'
    assert api.get(f'/api/lecturers/{lecturer}/ratings').json()['total'] == 0
    assert api.delete(f'/api/ratings/{ident}', params={'expected_updated_at': result.json()['UpdatedAt']}).status_code == 409
    with database.connect() as db:
        assert db.execute(select(func.count()).select_from(T['RatingAnswers'])).scalar_one() == 1


def test_no_comment_can_be_moderated(student):
    api, database, payload = student
    response = api.post('/api/ratings', json={**payload, 'Comment': None})
    assert response.status_code == 201
    ident = response.json()['RatingID']
    app.dependency_overrides[get_current_user] = lambda: Principal(None, True, 1)
    assert api.get('/api/admin/rating-queue').json()['total'] == 1
    assert api.put(f'/api/admin/comments/{ident}/moderation', json={'status': 'Approved', 'expected_status': 'Approved'}).status_code == 200


def test_auth_csrf_disabled_user_and_likes_blocked(student):
    api, database, payload = student
    assert api.post('/api/ratings', json=payload, headers={'Origin': 'https://other.example'}).status_code == 403
    assert api.post('/api/ratings', json=payload, headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert api.put('/api/ratings/9999/like').status_code == 404
    with database.begin() as db:
        db.execute(T['Users'].update().where(T['Users'].c.UserID == 1).values(IsEmailVerified=False))
    assert api.post('/api/ratings', json=payload).status_code == 403
    app.dependency_overrides.pop(get_current_user)
    assert api.post('/api/ratings', json=payload).status_code == 401


def test_transaction_rolls_back_on_audit_failure(student, monkeypatch):
    from fastapi import HTTPException
    from app.student2 import service
    api, database, payload = student
    def fail(*args):
        raise HTTPException(503, 'audit unavailable')
    monkeypatch.setattr(service, 'audit', fail)
    assert api.post('/api/ratings', json=payload).status_code == 503
    with database.connect() as db:
        for name in ('Ratings', 'RatingAnswers'):
            assert db.execute(select(func.count()).select_from(T[name])).scalar_one() == 0

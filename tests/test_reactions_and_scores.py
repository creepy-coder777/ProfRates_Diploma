from datetime import timedelta
from fastapi import HTTPException
from sqlalchemy import select, func
from app.main import app
from app.security import Principal, get_current_user
from app.student2.tables import TABLES as T
from test_student3 import student, create


def approve(api, ident):
    app.dependency_overrides[get_current_user] = lambda: Principal(None, True, 1)
    result = api.put(f'/api/admin/comments/{ident}/moderation', json={'status': 'Approved', 'expected_status': 'Pending'})
    assert result.status_code == 200, result.text
    app.dependency_overrides[get_current_user] = lambda: Principal(1, False)


def test_pending_and_rejected_text_do_not_hide_scores(student):
    api, database, payload = student
    record = create(student); ident = record['RatingID']; lid = payload['LecturerID']
    stats = api.get(f'/api/lecturers/{lid}/statistics').json()
    assert stats['TotalRatings'] == 1 and stats['AverageScore'] == 5
    assert stats['distribution'][-1]['count'] == 1
    assert api.get(f'/api/lecturers/{lid}/comments').json()['total'] == 0
    app.dependency_overrides[get_current_user] = lambda: Principal(None, True, 1)
    assert api.put(f'/api/admin/comments/{ident}/moderation', json={'status': 'Rejected', 'expected_status': 'Pending'}).status_code == 200
    assert api.get(f'/api/lecturers/{lid}/statistics').json()['AverageScore'] == 5
    assert api.get(f'/api/lecturers/{lid}/comments').json()['total'] == 0


def test_no_comment_is_immediate_and_new_rating_has_expiry(student):
    api, database, payload = student
    result = api.post('/api/ratings', json={**payload, 'Comment': '   '})
    assert result.status_code == 201, result.text
    record = result.json()
    assert record['Comment'] is None and record['Status'] == 'Approved'
    assert record['EditExpiry'] is not None
    assert api.get(f"/api/lecturers/{payload['LecturerID']}/statistics").json()['TotalRatings'] == 1
    assert api.get(f"/api/lecturers/{payload['LecturerID']}/comments").json()['total'] == 0
    assert api.put(f"/api/ratings/{record['RatingID']}/like").status_code == 404


def test_reactions_switch_clear_and_preserve_original_totals(student):
    api, database, payload = student
    record = create(student); ident = record['RatingID']
    assert api.put(f'/api/ratings/{ident}/like').status_code == 404
    approve(api, ident)
    with database.begin() as db:
        db.execute(T['Ratings'].update().where(T['Ratings'].c.RatingID == ident).values(Likes=8, Dislikes=3))
    url = f'/api/ratings/{ident}'
    first = api.put(url+'/like').json()
    assert (first['Likes'], first['Dislikes'], first['reaction']) == (9, 3, 1)
    assert api.put(url+'/like').json() == first
    other = api.put(url+'/dislike').json()
    assert (other['Likes'], other['Dislikes'], other['reaction']) == (8, 4, -1)
    assert api.get(url+'/reaction').json() == other
    assert api.delete(url+'/like').json() == other
    cleared = api.delete(url+'/reaction').json()
    assert (cleared['Likes'], cleared['Dislikes'], cleared['reaction']) == (8, 3, None)
    assert api.delete(url+'/reaction').json() == cleared
    with database.connect() as db:
        assert db.execute(select(func.count()).select_from(T['RatingReactions'])).scalar_one() == 0


def test_reaction_rolls_back_if_audit_fails(student, monkeypatch):
    from app.student3 import reactions
    api, database, payload = student
    record = create(student); ident = record['RatingID']; approve(api, ident)
    def fail(*args): raise HTTPException(503, 'audit unavailable')
    monkeypatch.setattr(reactions, 'audit', fail)
    assert api.put(f'/api/ratings/{ident}/like').status_code == 503
    with database.connect() as db:
        assert db.execute(select(func.count()).select_from(T['RatingReactions'])).scalar_one() == 0
        assert db.execute(select(T['Ratings'].c.Likes).where(T['Ratings'].c.RatingID == ident)).scalar_one() == 0


def test_edit_changes_score_immediately_and_hides_text(student):
    api, database, payload = student
    record = create(student); ident = record['RatingID']; approve(api, ident)
    assert api.put(f'/api/ratings/{ident}/like').status_code == 200
    latest = api.get(f'/api/me/ratings/{ident}').json()
    edited = {**payload, 'answers': [{**payload['answers'][0], 'Score': 2}], 'expected_updated_at': latest['UpdatedAt']}
    response = api.put(f'/api/ratings/{ident}', json=edited)
    assert response.status_code == 200, response.text
    assert response.json()['Status'] == 'Pending'
    assert api.get(f"/api/lecturers/{payload['LecturerID']}/statistics").json()['AverageScore'] == 2
    assert api.get(f"/api/lecturers/{payload['LecturerID']}/comments").json()['total'] == 0
    assert api.put(f'/api/ratings/{ident}/dislike').status_code == 404
    assert api.delete(f'/api/ratings/{ident}', params={'expected_updated_at': response.json()['UpdatedAt']}).status_code == 200
    with database.connect() as db:
        for name in ['Ratings', 'RatingAnswers', 'RatingReactions']:
            assert db.execute(select(func.count()).select_from(T[name])).scalar_one() == 0


def test_anonymous_reactions_are_rejected(student):
    api, database, payload = student
    app.dependency_overrides.pop(get_current_user)
    for method, suffix in [('get','reaction'),('put','like'),('put','dislike'),('delete','reaction')]:
        assert getattr(api, method)('/api/ratings/1/'+suffix).status_code == 401


def test_rankings_reuse_sql_procedure_and_hide_inactive_lecturers():
    from app.student3.router import rankings
    class Result:
        def __init__(self, rows): self.rows = rows
        def mappings(self): return self
        def all(self): return self.rows
        def __iter__(self): return iter(self.rows)
    class Database:
        def __init__(self): self.calls = []
        def execute(self, statement):
            self.calls.append(str(statement))
            if len(self.calls) == 1:
                return Result([{'LecturerID': 1, 'BayesianScore': 3.75, 'AverageScore': 5, 'TotalRatings': 3},
                               {'LecturerID': 2, 'BayesianScore': 4, 'AverageScore': 5, 'TotalRatings': 4}])
            if len(self.calls) == 2:
                return Result([{'LecturerID': 1, 'FirstName': 'Active', 'IsActive': True}])
            return Result([])
    db = Database()
    result = rankings(db=db)
    assert db.calls[0] == 'EXEC dbo.uspLecturerRankings'
    assert [r['LecturerID'] for r in result['items']] == [1]
    assert result['items'][0]['BayesianScore'] == 3.75

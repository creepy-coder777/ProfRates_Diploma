from datetime import datetime,timedelta
from pathlib import Path
import hashlib
import pytest
from sqlalchemy import select,func
from fastapi import HTTPException
from app.main import app
from app.security import Principal,get_current_user
from app.student2.tables import TABLES as T
from app.localization import english_patronymic,lecturer,DEMO_PORTRAITS
from test_student3 import student


def approved(student):
    api,_,payload=student
    result=api.post('/api/ratings',json={**payload,'Comment':'Հասկանալի բացատրություն'})
    assert result.status_code==201
    return result.json()


def patch(api,record,text='Լավ օրինակներ'):
    return api.patch(f"/api/ratings/{record['RatingID']}/comment",json={
        'Comment':text,'expected_updated_at':record['UpdatedAt']})


@pytest.mark.parametrize('status',['Pending','Approved','Rejected'])
def test_submitted_scores_cannot_be_changed_even_through_old_put(student,status):
    api,engine,payload=student
    record=approved(student)
    with engine.begin() as db:db.execute(T['Ratings'].update().values(Status=status))
    body={**payload,'answers':[dict(QuestionID=payload['answers'][0]['QuestionID'],Score=1)],
          'expected_updated_at':record['UpdatedAt']}
    assert api.put(f"/api/ratings/{record['RatingID']}",json=body).status_code==409
    with engine.connect() as db:
        assert db.execute(select(T['RatingAnswers'].c.Score)).scalar_one()==5


def test_approved_comment_can_change_without_answers_or_deadline_change(student):
    api,engine,_=student;record=approved(student)
    assert record['CanEditComment']
    result=patch(api,record)
    assert result.status_code==200,result.text
    new=result.json()
    assert new['Comment']=='Լավ օրինակներ' and new['Status']=='Approved'
    assert new['answers']==record['answers'] and new['EditExpiry']==record['EditExpiry']
    assert abs((datetime.fromisoformat(record['EditExpiry'])-datetime.fromisoformat(record['CreatedAt'])).total_seconds()-86400)<1


def test_pending_has_no_comment_edit_until_moderated(student):
    api,_,payload=student
    record=api.post('/api/ratings',json=payload).json()
    assert record['Status']=='Pending' and not record['CanEditComment']
    assert patch(api,record).status_code==409


def test_expired_and_exact_deadline_comments_rejected(student):
    api,engine,_=student;record=approved(student)
    with engine.begin() as db:
        db.execute(T['Ratings'].update().values(EditExpiry=func.current_timestamp()))
    assert patch(api,record).status_code==409
    assert not api.get(f"/api/me/ratings/{record['RatingID']}").json()['CanEditComment']


def test_rejection_reopens_24_hours_even_after_initial_deadline_and_does_not_extend_on_edit(student):
    api,engine,payload=student
    record=api.post('/api/ratings',json=payload).json();rid=record['RatingID']
    with engine.begin() as db:
        now=db.execute(select(func.current_timestamp())).scalar_one()
        db.execute(T['Ratings'].update().values(CreatedAt=now-timedelta(days=3),EditExpiry=now-timedelta(days=2)))
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,1)
    assert api.put(f'/api/admin/comments/{rid}/moderation',json={'status':'Rejected','expected_status':'Pending'}).status_code==200
    with engine.connect() as db:
        stored=db.execute(select(T['Ratings'])).mappings().one()
        expiry=stored['EditExpiry']
        assert abs((expiry-stored['UpdatedAt']).total_seconds()-86400)<1
    # Idempotent reject must not open another window.
    assert api.put(f'/api/admin/comments/{rid}/moderation',json={'status':'Rejected','expected_status':'Rejected'}).status_code==200
    app.dependency_overrides[get_current_user]=lambda:Principal(1,False)
    record=api.get(f'/api/me/ratings/{rid}').json();assert record['CanEditComment']
    result=patch(api,record)
    assert result.status_code==200 and result.json()['Status']=='Approved'
    assert result.json()['answers']==record['answers']
    assert datetime.fromisoformat(result.json()['EditExpiry'])==expiry


def test_manual_approval_does_not_extend_deadline(student):
    api,engine,payload=student
    record=api.post('/api/ratings',json=payload).json();rid=record['RatingID']
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,1)
    assert api.put(f'/api/admin/comments/{rid}/moderation',json={'status':'Approved','expected_status':'Pending'}).status_code==200
    with engine.connect() as db:
        assert db.execute(select(T['Ratings'].c.EditExpiry)).scalar_one()==datetime.fromisoformat(record['EditExpiry'])


def test_flagged_edit_is_pending_but_scores_remain_immutable(student):
    api,_,_=student;record=approved(student)
    result=patch(api,record,'Ապուշ։')
    assert result.status_code==200 and result.json()['Status']=='Pending'
    assert not result.json()['CanEditComment']
    assert result.json()['answers']==record['answers']
    assert result.json()['EditExpiry']==record['EditExpiry']


def test_comment_api_forbids_answer_injection_and_stale_versions(student):
    api,_,_=student;record=approved(student)
    url=f"/api/ratings/{record['RatingID']}/comment"
    body={'Comment':'Text','expected_updated_at':record['UpdatedAt']}
    assert api.patch(url,json={**body,'answers':[]}).status_code==422
    assert api.patch(url,json={**body,'LecturerID':999}).status_code==422
    assert api.patch(url,json={**body,'expected_updated_at':'2000-01-01T00:00:00'}).status_code==409
    assert api.patch(url,json={**body,'Comment':'x'*351}).status_code==422
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,1)
    assert api.patch(url,json=body).status_code==403
    app.dependency_overrides.pop(get_current_user)
    assert api.patch(url,json=body).status_code==401


def test_delete_and_recreate_cannot_bypass_score_lock(student):
    api,_,payload=student;record=approved(student)
    assert api.delete(f"/api/ratings/{record['RatingID']}",params={'expected_updated_at':record['UpdatedAt']}).status_code==409
    assert api.post('/api/ratings',json=payload).status_code==409


def test_comment_audit_failure_rolls_back(student,monkeypatch):
    api,_,_=student;record=approved(student)
    def fail(*args):raise HTTPException(503,'Audit unavailable')
    monkeypatch.setattr('app.student2.service.audit',fail)
    assert patch(api,record).status_code==503
    saved=api.get(f"/api/me/ratings/{record['RatingID']}").json()
    assert saved['Comment']==record['Comment'] and saved['answers']==record['answers']


@pytest.mark.parametrize(('name','expected'),[('Արամի','Aram'),('Հայկի','Hayk'),('Դավթի','Davit'),('Արայի','Ara'),('Կամոյի','Kamo'),('Րաֆֆի','Raffi'),('Arami','Aram'),(None,None)])
def test_patronymics_use_base_name_without_truncating_other_names(name,expected):
    assert english_patronymic(name)==expected


def test_each_selected_lecturer_has_distinct_local_portrait():
    root=Path(__file__).resolve().parents[1]
    digests=set()
    for identity,filename in DEMO_PORTRAITS.items():
        source=dict(zip(('FirstName','MiddleName','LastName'),identity))
        item=lecturer({**source,'PhotoUrl':None},'hy')
        content=(root/item['PhotoUrl'].lstrip('/')).read_bytes()
        digests.add(hashlib.sha256(content).hexdigest())
    assert len(digests)==10
    source={'FirstName':'Արամ','MiddleName':'Ռուբենի','LastName':'Ղազարյան','PhotoUrl':None}
    first=lecturer({**source,'LecturerID':1},'hy')
    duplicate=lecturer({**source,'LecturerID':16},'hy')
    assert first['PhotoUrl']==duplicate['PhotoUrl']
    assert lecturer({**source,'LecturerID':16},'en')['PhotoUrl']==first['PhotoUrl']
    assert lecturer({**source,'MiddleName':'Արմենի'},'hy')['PhotoUrl'] is None
    assert lecturer({**source,'LastName':'Այլազգանուն'},'hy')['PhotoUrl'] is None
    assert lecturer({**source,'MiddleName':None},'hy')['PhotoUrl'] is None
    assert lecturer({**source,'FirstName':'  Արամ  '},'hy')['PhotoUrl']==first['PhotoUrl']
    assert lecturer({**source,'PhotoUrl':'/frontend/real.jpg'},'hy')['PhotoUrl']=='/frontend/real.jpg'



def test_login_has_accessible_password_toggle_and_no_signup_prompt():
    from bs4 import BeautifulSoup
    root=Path(__file__).resolve().parents[1]/'frontend'
    for name,prompt in [('login_arm.html','Չունեք հաշիվ'),('login_eng.html',"Don't have an account")]:
        soup=BeautifulSoup((root/name).read_text('utf-8'),'html.parser')
        assert prompt not in soup.get_text()
        eye=soup.select_one('button.password-toggle')
        assert eye['type']=='button' and eye['aria-pressed']=='false'
        assert soup.find(id=eye['aria-controls'])['type']=='password'

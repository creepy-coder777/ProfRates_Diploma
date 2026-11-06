"""Provisioning uses existing tables; curriculum gaps never create fictional courses."""
from datetime import date,timedelta
from pathlib import Path
import pytest
from sqlalchemy import select,func
from app.student2.tables import TABLES as T
from app.student3.moderation import review_required,rating_status
from test_accounts import auth_api,post,provision,sign_in,EMAIL
from test_student3 import student


@pytest.mark.parametrize('text',[None,'','Վատ է բացատրում, դժգոհ եմ։','անարդար է գնահատում','classic classroom','shittyness','Տխմարություն'])
def test_normal_criticism_is_approved(text):
    assert rating_status(text)=='Approved'


@pytest.mark.parametrize('text',['ԱՊՈՒՇ։','Դու տխմար ես','IDIOT!','Ты идиот.','ՔԵԶ   ԿՍՊԱՆԵՄ','I will kill you','f\u200buck'])
def test_flagged_words_and_phrases_wait_for_review(text):
    assert review_required(text) and rating_status(text)=='Pending'


def test_safe_comment_is_public_and_counted_immediately(student):
    api,engine,payload=student
    result=api.post('/api/ratings',json={**payload,'Comment':'Վատ է բացատրում, դժգոհ եմ։'})
    assert result.status_code==201 and result.json()['Status']=='Approved'
    lid=payload['LecturerID']
    assert api.get(f'/api/lecturers/{lid}/statistics').json()['TotalRatings']==1
    assert api.get(f'/api/lecturers/{lid}/comments').json()['total']==1


def test_admin_creation_syncs_current_curriculum_and_filters(auth_api):
    client,engine,_=auth_api
    today=date.today()
    with engine.begin() as db:
        db.execute(T['AcademicTerms'].insert().values(TermID=1,AcademicYearStart=2026,TermNumber=1,
            NameHy='Test',StartsOn=today-timedelta(days=1),EndsOn=today+timedelta(days=1)))
        lid=db.execute(T['Lecturers'].insert().values(FirstName='Demo',IsActive=True,ViewCount=0)).inserted_primary_key[0]
        cid=db.execute(T['Courses'].insert().values(LecturerID=lid,SpecializationID=1,Name='Current course',
            CurriculumSemesterNumber=1,IsActive=True)).inserted_primary_key[0]
    response=provision(client)
    assert response.status_code==201 and response.json()['academic_status']=='ready'
    uid=response.json()['student']['UserID']
    with engine.connect() as db:
        assert db.execute(select(T['StudentCourses'].c.CourseID).where(T['StudentCourses'].c.UserID==uid)).scalars().all()==[cid]
        progress=db.execute(select(T['StudentAcademicProgress']).where(T['StudentAcademicProgress'].c.UserID==uid)).mappings().one()
        assert progress['SemesterNumber']==1 and progress['IsCurrent']
    sign_in(client,'admin@example.test',admin=True)
    for key in ['institute_id','chair_id','specialization_id','group_id','year']:
        result=client.get('/api/admin/users',params={key:1,'q':EMAIL})
        assert result.status_code==200 and result.json()['total']==1
        assert result.json()['items'][0]['StudyYear']==1
        assert client.get('/api/admin/users',params={key:2,'q':EMAIL}).json()['total']==0
    assert client.get('/api/admin/users',params={'faculty_id':1,'q':EMAIL}).json()['total']==0
    assert client.get('/api/admin/users',params={'year':5}).status_code==422
    assert sign_in(client).status_code==200
    options=client.get('/api/me/rating-options').json()
    assert str(cid) in str(options)


def test_curriculum_gap_is_reported_without_invented_links(auth_api):
    client,engine,_=auth_api
    today=date.today()
    with engine.begin() as db:
        db.execute(T['AcademicTerms'].insert().values(TermID=1,AcademicYearStart=2026,TermNumber=1,
            NameHy='Test',StartsOn=today-timedelta(days=1),EndsOn=today+timedelta(days=1)))
    result=provision(client)
    assert result.json()['academic_status']=='curriculum-missing'
    with engine.connect() as db:
        assert db.execute(select(func.count()).select_from(T['Courses'])).scalar_one()==0
        assert db.execute(select(func.count()).select_from(T['StudentCourses'])).scalar_one()==0


def test_existing_inactive_parent_cannot_receive_new_student(auth_api):
    client,engine,_=auth_api
    with engine.begin() as db:db.execute(T['Chairs'].update().values(IsActive=False))
    assert provision(client).status_code==422


def test_signup_links_and_roster_ui_removed():
    from bs4 import BeautifulSoup
    root=Path(__file__).resolve().parents[1]/'frontend'
    for p in root.rglob('*.html'):
        soup=BeautifulSoup(p.read_text('utf-8'),'html.parser')
        assert not soup.select('a[href*="sign_up_"]'),p
    script=(root/'admin_portal/js_folder/accounts.js').read_text('utf-8')
    assert '/api/admin/student-roster' not in script


def test_demo_portraits_preserve_real_photos_and_unknown_avatar():
    from app.localization import lecturer
    root=Path(__file__).resolve().parents[1]
    for ident,name,middle,last,filename in [(2,'Մարինե','Սուրենի','Հովհաննիսյան','lecturer-02.jpg'),(3,'Վահե','Հրանտի','Մկրտչյան','lecturer-03.jpg')]:
        result=lecturer({'LecturerID':ident,'FirstName':name,'MiddleName':middle,'LastName':last,'PhotoUrl':None},'hy')
        assert result['PhotoIsDemo']
        assert result['PhotoUrl'].endswith(filename)
        assert (root/result['PhotoUrl'].lstrip('/')).is_file()
    original={'FirstName':'Անի','PhotoUrl':'/frontend/real.jpg'}
    assert lecturer(original,'hy')==original
    assert lecturer({'FirstName':'Unknown','PhotoUrl':None},'hy')['PhotoUrl'] is None


def test_dashboard_average_counts_only_approved(student):
    from app.main import app
    from app.security import Principal,get_current_user
    api,_,payload=student
    result=api.post('/api/ratings',json=payload)
    assert result.status_code==201 and result.json()['Status']=='Pending'
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,1)
    assert api.get('/api/admin/dashboard').json()['average_score'] is None
    rid=result.json()['RatingID']
    assert api.put(f'/api/admin/comments/{rid}/moderation',json={'status':'Approved','expected_status':'Pending'}).status_code==200
    assert api.get('/api/admin/dashboard').json()['average_score']==5

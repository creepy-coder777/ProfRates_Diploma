"""Regression checks that do not require sockets or a production database."""
from datetime import datetime
from pathlib import Path
import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from starlette.requests import Request
from bs4 import BeautifulSoup
from sqlalchemy import select
from app.localization import lecturer, department, transliterate
from app.auth.schemas import LoginInput, RegisterInput
from app.security import Principal
from app.student2.tables import TABLES as T
from app.student3.dependencies import get_student
from app.student3.schemas import RatingInput
from app.student3 import service
from app.student3.router import mine


def test_english_names_and_departments_preserve_source():
    original={'FirstName':'Արամ','LastName':'Սարգսյան','Chairs':['Համակարգչային համակարգեր և ցանցեր']}
    translated=lecturer(original,'en')
    assert translated['FirstName']=='Aram'
    assert translated['LastName']=='Sargsyan'
    assert translated['Chairs']==['Computer Systems and Networks']
    assert original['FirstName']=='Արամ'
    assert lecturer(original,'hy')==original
    assert department('Նոր ամբիոն')=='Նոր ամբիոն'
    assert transliterate('Սուրեն')=='Suren'


@pytest.mark.parametrize('values',[
    {'Email':'','Password':'x'}, {'Email':'x@gmail.com','Password':'x'},
    {'Email':'a@polytechnic.am','Password':''},
    {'Email':'a@@polytechnic.am','Password':'secret'},
])
def test_invalid_login(values):
    with pytest.raises(ValidationError):LoginInput(**values)


def test_registration_and_password_validation():
    values=dict(Email='a@polytechnic.am',Password='safe-password-123')
    assert RegisterInput(**values).Email=='a@polytechnic.am'
    for patch in ({'FirstName':' '},{'LastName':''},{'ChairID':0},{'ChairID':True},{'Password':'123'}):
        with pytest.raises(ValidationError):RegisterInput(**{**values,**patch})
    assert LoginInput(Email=' A@POLYTECHNIC.AM ',Password=' secret ').Password==' secret '


def test_authentication_uses_real_router():
    from app.auth.router import router
    paths={r.path for r in router.routes}
    assert {'/api/auth/student/forgot-password','/api/auth/admin/forgot-password',
            '/api/auth/student/reset-password','/api/auth/admin/reset-password'} <= paths


def test_page_wiring_and_no_static_personal_counts():
    root=Path(__file__).resolve().parents[1]/'frontend'
    for filename in ('home_eng.html','home_arm_guest.html','rate_eng.html','ratings_eng.html','login_eng.html'):
        soup=BeautifulSoup((root/filename).read_text('utf-8'),'html.parser')
        scripts=[script['src'].split('?')[0] for script in soup.select('script[src]')]
        assert scripts.index('js_codes/api.js')<scripts.index('js_codes/ui_session.js')
        assert soup.select_one('link[href^="ui-fixes.css?v="]')
        for link in soup.select('a[href*="ratings_"]'):assert link.has_attr('hidden')
        if filename.startswith('ratings_'):assert soup.select_one('.subtitle').get_text(strip=True)==''
        if filename.startswith(('login_','sign_up_')):
            assert not soup.select('script:not([src])')
            assert 'js_codes/ui_auth_forms.js' in scripts
    auth_script=(root/'js_codes/ui_auth_forms.js').read_text('utf-8')
    assert "label.after(note)" in auth_script
    assert "input.setAttribute('aria-describedby', note.id)" in auth_script
    root=Path(__file__).resolve().parents[1]/'frontend'
    for filename,language,portal in [
        ('account_recovery.html','hy','student'),
        ('account_recovery_en.html','en','student'),
        ('admin_portal/account_recovery_arm.html','hy','admin'),
        ('admin_portal/account_recovery_eng.html','en','admin'),
    ]:
        soup=BeautifulSoup((root/filename).read_text('utf-8'),'html.parser')
        page=soup.select_one('[data-recovery-role]')
        assert page['data-recovery-role']==portal and page['data-recovery-language']==language
        assert not soup.select('select')


def test_rating_persists_and_mine_is_scoped_to_verified_student(database):
    request=Request({'type':'http','method':'GET','headers':[],'scheme':'http','server':('test',80),'path':'/','query_string':b''})
    with database.begin() as db:
        actor=get_student(request,Principal(1,False),db)
        assert actor.user_id==1 and not actor.is_admin
        with pytest.raises(HTTPException):get_student(request,Principal(None,True,1),db)
        lecturer_id=db.execute(T['Lecturers'].insert().values(FirstName='Արամ',LastName='Սարգսյան',IsActive=True,ViewCount=0)).inserted_primary_key[0]
        course_id=db.execute(T['Courses'].insert().values(SpecializationID=1,LecturerID=lecturer_id,Name='Test',CurriculumSemesterNumber=1,IsActive=True)).inserted_primary_key[0]
        term=db.execute(T['AcademicTerms'].insert().values(AcademicYearStart=2026,TermNumber=1,NameHy='Test')).inserted_primary_key[0]
        db.execute(T['StudentAcademicProgress'].insert().values(UserID=1,TermID=term,SemesterNumber=1,IsCurrent=True))
        db.execute(T['StudentCourses'].insert().values(UserID=1,CourseID=course_id,EnrolledAt=datetime.now()))
        question=db.execute(T['Questions'].insert().values(Text='Test',Category='Teaching',SortOrder=1,IsActive=True)).inserted_primary_key[0]
        payload=RatingInput(LecturerID=lecturer_id,CourseID=course_id,TermID=term,Comment='Review',answers=[{'QuestionID':question,'Score':5}])
        assert mine((1,20),actor,db)['total']==0
        with pytest.raises(HTTPException):service.validate_answers(db,[])
        saved=service.create_rating(db,actor,payload)
        assert saved['Status']=='Approved'
        result=mine((1,20),actor,db)
        assert result['total']==1
        assert result['items'][0]['RatingID']==saved['RatingID']
        assert result['items'][0]['answers']==[{'QuestionID':question,'Score':5}]
        with pytest.raises(HTTPException):service.private_rating(db,saved['RatingID'],2)
        assert db.execute(select(T['Ratings'].c.UserID)).scalar_one()==1
        from app.student2.router import public_lecturer
        assert public_lecturer(lecturer_id,'en',db)['FirstName']=='Aram'
        second_course=db.execute(T['Courses'].insert().values(SpecializationID=1,LecturerID=lecturer_id,Name='Second',CurriculumSemesterNumber=1,IsActive=True)).inserted_primary_key[0]
        db.execute(T['StudentCourses'].insert().values(UserID=1,CourseID=second_course,EnrolledAt=datetime.now()))
        second=service.create_rating(db,actor,payload.model_copy(update={'CourseID':second_course}))
        assert [item['RatingID'] for item in mine((1,20),actor,db)['items']]==[second['RatingID'],saved['RatingID']]


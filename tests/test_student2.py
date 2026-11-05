from datetime import datetime
from sqlalchemy import select,func,text
from sqlalchemy.dialects import mssql
from app.main import app
from app.security import Principal,get_current_user
from app.student2.tables import TABLES as T
from app.student2.service import lecturer_query


def lecturer(api,name='Արամ'):
    r=api.post('/api/admin/lecturers',json={'FirstName':name,'LastName':'Պետրոսյան'})
    assert r.status_code==201,r.text
    return r.json()['LecturerID']

def create(api,resource,body):
    r=api.post('/api/admin/academic/'+resource,json=body);assert r.status_code==201,r.text;return r.json()

def curriculum(api):
    i=create(api,'institutes',{'Name':'Ինստիտուտ','ShortName':'Ի'})['InstituteID']
    f=create(api,'faculties',{'Name':'Ֆակուլտետ','ShortName':'Ֆ'})['FacultyID']
    ch=create(api,'chairs',{'Name':'Ամբիոն','ShortName':'Ա','InstituteID':i})['ChairID']
    sp=create(api,'specializations',{'Name':'Մասնագիտացում','Code':'0611','ChairID':ch})['SpecializationID']
    g=create(api,'groups',{'GroupCode':'ՏՏ319','SpecializationID':sp,'EnrollmentYear':2023})['GroupID']
    l=lecturer(api)
    c=create(api,'courses',{'Name':'Ծրագրավորում','SpecializationID':sp,'LecturerID':l,'CurriculumSemesterNumber':1})['CourseID']
    return dict(institutes=i,faculties=f,chairs=ch,specializations=sp,groups=g,courses=c,lecturer=l)

def question(api,text='Հարց'):
    r=api.post('/api/admin/questions',json={'Text':text,'Category':'Բաժին','SortOrder':1});assert r.status_code==201,r.text;return r.json()['QuestionID']

def rating(db,l,q,c=None):
    rid=db.execute(T['Ratings'].insert().values(UserID=1,LecturerID=l,Comment='Հանրային կարծիք',Status='Pending',Likes=0,Dislikes=0,CreatedAt=datetime.now(),UpdatedAt=datetime.now(),CourseID=c)).inserted_primary_key[0]
    db.execute(T['RatingAnswers'].insert().values(RatingID=rid,QuestionID=q,Score=5));return rid

def test_lecturer_persist_search_pagination_deactivate(api,database):
    i=lecturer(api);lecturer(api,'Անահիտ')
    assert api.get('/api/lecturers?q=Արամ').json()['total']==1
    assert api.get('/api/lecturers?page_size=1&page=2').json()['items'][0]['FirstName']=='Անահիտ'
    assert api.put(f'/api/admin/lecturers/{i}',json={'FirstName':'Արմեն'}).status_code==200
    with database.connect() as db:assert db.execute(select(T['Lecturers'].c.FirstName).where(T['Lecturers'].c.LecturerID==i)).scalar_one()=='Արմեն'
    assert api.delete(f'/api/admin/lecturers/{i}').status_code==200
    assert api.get('/api/lecturers').json()['total']==1
    assert api.get('/api/admin/lecturers?active=false').json()['items'][0]['LecturerID']==i
    assert api.get(f'/api/lecturers/{i}').status_code==404
    assert api.post('/api/admin/lecturers',json={'FirstName':'x','ViewCount':10}).status_code==422

def test_academic_crud_and_filters(api):
    c=curriculum(api)
    for param,key in [('chair_id','chairs'),('institute_id','institutes'),('specialization_id','specializations'),('course_id','courses')]:
        assert api.get('/api/lecturers',params={param:c[key]}).json()['total']==1
    assert api.get('/api/lecturers',params={'faculty_id':c['faculties']}).json()['total']==0
    assert api.post('/api/admin/academic/chairs',json={'Name':'X','ShortName':'X','InstituteID':c['institutes'],'FacultyID':c['faculties']}).status_code==422
    assert api.post('/api/admin/academic/groups',json={'GroupCode':'X','SpecializationID':999,'EnrollmentYear':2025}).status_code==404
    for resource,key in [('courses','CourseID'),('groups','GroupID'),('specializations','SpecializationID'),('chairs','ChairID'),('faculties','FacultyID'),('institutes','InstituteID')]:
        r=api.get('/api/admin/academic/'+resource).json()['items'][0];r.pop(key)
        if 'Name'in r:r['Name']+=' նոր'
        else:r['GroupCode']='ՏՏ320'
        assert api.put(f'/api/admin/academic/{resource}/{c[resource]}',json=r).status_code==200
    for resource in ['courses','groups','specializations','chairs','faculties','institutes']:
        assert api.delete(f'/api/admin/academic/{resource}/{c[resource]}').status_code==200
        assert api.get('/api/academic/'+resource).json()['total']==0

def test_course_links(api):
    c=curriculum(api);l=lecturer(api,'Երկրորդ')
    assert api.put(f'/api/admin/courses/{c["courses"]}/lecturer',json={'LecturerID':l}).status_code==200
    body={'UserID':1,'CourseID':c['courses']};r=api.post('/api/admin/student-courses',json=body);assert r.status_code==201
    assert api.post('/api/admin/student-courses',json=body).status_code==409
    assert api.get('/api/admin/student-courses?user_id=1').json()['total']==1
    assert api.delete('/api/admin/student-courses/'+str(r.json()['StudentCourseID'])).status_code==200
    assert api.get('/api/admin/student-courses').json()['total']==0

def test_question_history_order_deactivate_export(api,database):
    l=lecturer(api);q=question(api,'Հին հարց')
    with database.begin() as db:rating(db,l,q)
    r=api.put(f'/api/admin/questions/{q}',json={'Text':'Նոր հարց','Category':'Բաժին','SortOrder':1})
    assert r.status_code==200,r.text
    new=r.json()['question']['QuestionID'];assert new!=q
    with database.connect() as db:
        assert db.execute(select(T['RatingAnswers'].c.QuestionID)).scalar_one()==q
        assert db.execute(select(T['Questions'].c.Text).where(T['Questions'].c.QuestionID==q)).scalar_one()=='Հին հարց'
    other=question(api,'Այլ հարց')
    assert api.put('/api/admin/questions/order',json={'question_ids':[other,new]}).status_code==200
    assert [x['QuestionID']for x in api.get('/api/questions').json()['items']]==[other,new]
    assert api.put('/api/admin/questions/order',json={'question_ids':[other]}).status_code==409
    assert api.put('/api/admin/questions/order',json={'question_ids':[new,new]}).status_code==422
    assert 'Նոր հարց'in api.get('/api/admin/questions/export').text
    assert api.delete(f'/api/admin/questions/{new}').status_code==200
    with database.connect() as db:assert db.execute(select(func.count()).select_from(T['RatingAnswers'])).scalar_one()==1

def test_moderation_summary_anonymity_and_idempotency(api,database):
    l=lecturer(api);q=question(api)
    with database.begin() as db:r=rating(db,l,q)
    url=f'/api/admin/comments/{r}/moderation'
    assert api.get(f'/api/lecturers/{l}/comments').json()['total']==0
    assert api.get('/api/admin/comments?status=Pending').json()['total']==1
    assert api.put(url,json={'status':'Approved','expected_status':'Pending'}).status_code==200
    public=api.get(f'/api/lecturers/{l}/comments').json();assert public['total']==1
    assert not {'UserID','StudentName','StudentEmail'} & public['items'][0].keys()
    assert api.get(f'/api/lecturers/{l}').json()['AverageScore']==5.0
    with database.connect() as db:before=db.execute(select(func.count()).select_from(T['ActivityLogs'])).scalar_one()
    assert api.put(url,json={'status':'Approved','expected_status':'Approved'}).status_code==200
    with database.connect() as db:assert db.execute(select(func.count()).select_from(T['ActivityLogs'])).scalar_one()==before
    assert api.put(url,json={'status':'Rejected','expected_status':'Pending'}).status_code==409
    assert api.put(url,json={'status':'Rejected','expected_status':'Approved'}).status_code==200
    assert api.get(f'/api/lecturers/{l}/comments').json()['total']==0
    assert api.get(f'/api/lecturers/{l}').json()['TotalRatings']==1

def test_course_history_preserved(api,database):
    c=curriculum(api);new=lecturer(api,'Նոր');q=question(api)
    with database.begin() as db:rating(db,c['lecturer'],q,c['courses'])
    assert api.put(f'/api/admin/courses/{c["courses"]}/lecturer',json={'LecturerID':new}).status_code==409

def test_all_admin_routes_require_verified_admin(api):
    for role in [Principal(1,False),Principal(None,True,None),Principal(None,True,999)]:
        app.dependency_overrides[get_current_user]=lambda:role
        paths=app.openapi()['paths']
        checked=0
        for path,methods in paths.items():
            if path.startswith('/api/admin/'):
                path=path.replace('{ident}','1').replace('{resource_name}','institutes')
                for method in methods:
                    if method not in ['get','post','put','delete']:continue
                    r=api.request(method.upper(),path,json={});assert r.status_code==403,(path,r.status_code)
                    checked+=1
        assert checked>=28

def test_search_csv_validation(api):
    lecturer(api,'=HYPERLINK("x")')
    assert api.get('/api/lecturers',params={'q':"' OR 1=1 --"}).json()['total']==0
    assert "'=HYPERLINK"in api.get('/api/admin/lecturers/export').text
    assert api.get('/api/lecturers?page_size=1000').status_code==422
    assert api.post('/api/admin/academic/not-a-table',json={}).status_code==404

def test_mssql_compiles_bind_parameters():
    sql=str(lecturer_query(q="O'Neil",chair_id=1).offset(20).limit(20).compile(dialect=mssql.dialect()))
    assert 'dbo.[Lecturers]'in sql
    assert 'ROW_NUMBER'in sql or 'OFFSET'in sql
    assert "O'Neil"not in sql

def test_audit_failure_rolls_back_whole_operation(api,database,monkeypatch):
    from app.student2 import dependencies
    from app.student2.dependencies import get_db
    app.dependency_overrides.pop(get_db)
    monkeypatch.setattr(dependencies,'get_engine',lambda:database)
    with database.begin() as db:db.execute(text('DROP TABLE ActivityLogs'))
    response=api.post('/api/admin/lecturers',json={'FirstName':'Չպահպանվող'})
    assert response.status_code==503,response.text
    with database.connect() as db:assert db.execute(select(func.count()).select_from(T['Lecturers'])).scalar_one()==0

def test_public_ignores_inactive_override_and_invalid_admin_id(api):
    lid=lecturer(api)
    api.delete(f'/api/admin/lecturers/{lid}')
    assert api.get('/api/lecturers?active=false').json()['total']==0
    app.dependency_overrides[get_current_user]=lambda:Principal(None,True,999)
    assert api.post('/api/admin/lecturers',json={'FirstName':'Կեղծ'}).status_code==403

def test_unanswered_question_edit_in_place(api):
    q=question(api)
    result=api.put(f'/api/admin/questions/{q}',json={'Text':'Փոփոխված','Category':'Բաժին','SortOrder':5})
    assert result.status_code==200
    assert result.json()['replaced_question_id'] is None
    assert result.json()['question']['QuestionID']==q

def test_untrusted_origin_rejected(api):
    r=api.post('/api/admin/lecturers',json={'FirstName':'Արամ'},headers={'Origin':'https://untrusted.example'})
    assert r.status_code==403

def test_success_committed_before_response(api,database,monkeypatch):
    from app.student2 import dependencies
    from app.student2.dependencies import get_db
    app.dependency_overrides.pop(get_db)
    monkeypatch.setattr(dependencies,'get_engine',lambda:database)
    lid=lecturer(api)
    with database.connect() as db:
        assert db.execute(select(T['Lecturers'].c.LecturerID).where(T['Lecturers'].c.LecturerID==lid)).scalar_one()==lid


def test_api_and_frontend_use_same_question_source(api):
    from app.config import ROOT
    from bs4 import BeautifulSoup
    question(api,'Միասնական հարց')
    assert len(api.get('/api/questions').json()['items'])==1
    for filename in ['rate_arm.html','admin_portal/RatingQuestions_arm.html']:
        s=BeautifulSoup((ROOT/'frontend'/filename).read_text(encoding='utf-8'),'html.parser')
        assert not s.select('.question-item')
    assert '/api/questions' in (ROOT/'frontend/js_codes/student2_rate.js').read_text(encoding='utf-8')
    assert '/api/admin/questions' in (ROOT/'frontend/admin_portal/js_folder/student2_questions.js').read_text(encoding='utf-8')

def test_external_audit_single_provider(api,database,monkeypatch):
    import sys,types
    from app import config
    module=types.ModuleType('test_audit_adapter');calls=[]
    def record(db,actor,action,target):
        calls.append((actor.admin_id,action,target))
        db.execute(T['ActivityLogs'].insert().values(AdminID=actor.admin_id,ActionType=action,Target=target,Status='Success',CreatedAt=datetime.now()))
    module.record=record;monkeypatch.setitem(sys.modules,'test_audit_adapter',module)
    monkeypatch.setattr(config,'get_settings',lambda:types.SimpleNamespace(audit_provider='test_audit_adapter:record'))
    lecturer(api)
    assert len(calls)==1
    with database.connect() as db:assert db.execute(select(func.count()).select_from(T['ActivityLogs'])).scalar_one()==1

def test_export_respects_academic_search(api):
    create(api,'institutes',{'Name':'Առաջին','ShortName':'Ա'})
    create(api,'institutes',{'Name':'Երկրորդ','ShortName':'Ե'})
    result=api.get('/api/admin/academic/institutes/export?q=Առաջին')
    assert result.status_code==200
    assert 'Առաջին'in result.text and 'Երկրորդ'not in result.text

def test_student_course_search_and_export(api,database):
    c=curriculum(api)
    with database.begin() as db:db.execute(T['Users'].update().where(T['Users'].c.UserID==1).values(GroupID=c['groups']))
    api.post('/api/admin/student-courses',json={'UserID':1,'CourseID':c['courses']})
    for term in ['Ուսանող','Փորձ','Ուսանող Փորձ','ՏՏ319','Ծրագրավորում']:
        data=api.get('/api/admin/student-courses',params={'q':term}).json()
        assert data['total']==1,(term,data)
        assert data['items'][0]['CourseName']=='Ծրագրավորում'
        csv=api.get('/api/admin/student-courses/export',params={'q':term})
        assert csv.headers['x-export-rows']=='1'
    for term in ["' OR 1=1 --",'%', '_','Չկա']:
        assert api.get('/api/admin/student-courses',params={'q':term}).json()['total']==0
    assert api.get('/api/admin/student-courses',params={'q':'Փորձ','user_id':999}).json()['total']==0
    assert api.get('/api/admin/student-courses',params={'q':'Փորձ','course_id':999}).json()['total']==0
    assert api.get('/api/admin/student-courses/export?q=Չկա').headers['x-export-rows']=='0'
    assert api.get('/api/admin/student-courses',params={'q':'x'*151}).status_code==422


def test_public_comment_pagination(api,database):
    lid=lecturer(api);qid=question(api)
    with database.begin() as db:
        for i in range(23):
            rid=rating(db,lid,qid)
            db.execute(T['Ratings'].update().where(T['Ratings'].c.RatingID==rid).values(Status='Approved',Comment=f'Կարծիք {i}'))
    first=api.get(f'/api/lecturers/{lid}/comments?page=1&page_size=20').json()
    second=api.get(f'/api/lecturers/{lid}/comments?page=2&page_size=20').json()
    assert first['total']==second['total']==23
    assert len(first['items'])==20 and len(second['items'])==3
    assert not {x['RatingID']for x in first['items']} & {x['RatingID']for x in second['items']}

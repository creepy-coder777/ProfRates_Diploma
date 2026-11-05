import csv, io
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select, func, or_
from app.student2 import service as svc
from app.student2.tables import TABLES as T, admin_ratings
from app.student2.schemas import LecturerInput, QuestionInput, Reorder, StudentCourseInput, Assignment, Moderation
from app.student2.dependencies import get_db, get_actor

public=APIRouter(prefix='/api',tags=['Հանրային տվյալներ'])
admin=APIRouter(prefix='/api/admin',tags=['Երկրորդ ուսանող'],dependencies=[Depends(get_actor)])

def filters(q: str = Query('',max_length=150), active: bool | None = None,
            chair_id: int | None = Query(None,gt=0), institute_id: int | None = Query(None,gt=0),
            faculty_id: int | None = Query(None,gt=0),specialization_id: int | None = Query(None,gt=0),course_id: int | None = Query(None,gt=0), sort: str = Query("id",pattern="^(id|highest|lowest|a-z|z-a)$")):
    return dict(q=q,active=active,chair_id=chair_id,institute_id=institute_id,faculty_id=faculty_id,specialization_id=specialization_id,course_id=course_id,sort=sort)

def pagination(page: int = Query(1,ge=1,le=100000), page_size: int = Query(20,ge=1,le=100)):
    return page,page_size

def lecturer_list(db,f,p):
    aliases = svc.lecturer_search_aliases(db, f.get('q', ''))
    result=svc.page(db,svc.lecturer_query(**f, alias_matches=aliases),T['Lecturers'].c.LecturerID,*p)
    svc.lecturer_departments(db,result['items'])
    return result

def csv_response(items,filename):
    output=io.StringIO(newline=''); output.write('\ufeff')
    if items:
        writer=csv.DictWriter(output,fieldnames=list(items[0]));writer.writeheader()
        for item in items:
            safe={}
            for k,v in item.items():
                v='' if v is None else ', '.join(map(str,v)) if isinstance(v,list) else str(v)
                if v.lstrip().startswith(('=','+','-','@','\t','\r','\n')): v="'"+v
                safe[k]=v
            writer.writerow(safe)
    return Response(output.getvalue().encode('utf-8'),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{filename}"','X-Export-Rows':str(len(items))})

@public.get('/lecturers')
def public_lecturers(lang: str = Query("hy", pattern="^(hy|en)$"),f=Depends(filters),p=Depends(pagination),db=Depends(get_db,scope="function")):
    f['active']=True
    from app.localization import lecturer_page
    return lecturer_page(lecturer_list(db,f,p),lang)

@public.get('/lecturers/{ident}')
def public_lecturer(ident:int,lang: str = Query("hy", pattern="^(hy|en)$"),db=Depends(get_db,scope="function")):
    result=db.execute(svc.lecturer_query().where(T['Lecturers'].c.LecturerID==ident)).mappings().first()
    if not result: raise HTTPException(404,'Դասախոսը չի գտնվել։')
    item=dict(result);svc.lecturer_departments(db,[item])
    from app.localization import lecturer
    return lecturer(item,lang)

@admin.get('/lecturers/export')
def lecturer_export(f=Depends(filters),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return csv_response(lecturer_list(db,f,p)['items'],'lecturers.csv')

@admin.get('/lecturers')
def lecturers(f=Depends(filters),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return lecturer_list(db,f,p)

@admin.post('/lecturers',status_code=201)
def add_lecturer(payload:LecturerInput,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.create(db,T['Lecturers'],'LecturerID',{**payload.model_dump(),'ViewCount':0},actor)

@admin.put('/lecturers/{ident}')
def edit_lecturer(ident:int,payload:LecturerInput,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.edit(db,T['Lecturers'],'LecturerID',ident,payload.model_dump(),actor)

@admin.delete('/lecturers/{ident}')
def deactivate_lecturer(ident:int,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.deactivate(db,T['Lecturers'],'LecturerID',ident,actor)

@public.get('/questions')
def active_questions(db=Depends(get_db,scope="function")):
    t=T['Questions']
    return {'items':[dict(r) for r in db.execute(select(t).where(t.c.IsActive==True).order_by(t.c.SortOrder,t.c.QuestionID)).mappings()]}

@admin.get('/questions/export')
def question_export(db=Depends(get_db,scope="function"),active:bool|None=None):
    t=T['Questions'];stmt=select(t)
    if active is not None:stmt=stmt.where(t.c.IsActive==active)
    return csv_response([dict(r) for r in db.execute(stmt.order_by(t.c.SortOrder,t.c.QuestionID)).mappings()],'questions.csv')

@admin.get('/questions')
def questions(db=Depends(get_db,scope="function"),active:bool|None=None):
    t=T['Questions'];stmt=select(t)
    if active is not None:stmt=stmt.where(t.c.IsActive==active)
    return {'items':[dict(r) for r in db.execute(stmt.order_by(t.c.SortOrder,t.c.QuestionID)).mappings()]}

@admin.post('/questions',status_code=201)
def add_question(payload:QuestionInput,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.create(db,T['Questions'],'QuestionID',payload.model_dump(),actor)

@admin.put('/questions/order')
def reorder(payload:Reorder,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    t=T['Questions'];ids=list(db.execute(select(t.c.QuestionID).where(t.c.IsActive==True)).scalars())
    if set(ids)!=set(payload.question_ids):raise HTTPException(409,'Ուղարկեք բոլոր ակտիվ հարցերը՝ առանց բաց թողնելու։ Թարմացրեք էջը։')
    for i,ident in enumerate(payload.question_ids,1):db.execute(t.update().where(t.c.QuestionID==ident).values(SortOrder=i))
    svc.audit(db,actor,'Reorder','Questions');return {'question_ids':payload.question_ids}

@admin.put('/questions/{ident}')
def edit_question(ident:int,payload:QuestionInput,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.question_edit(db,ident,payload.model_dump(),actor)

@admin.delete('/questions/{ident}')
def deactivate_question(ident:int,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.deactivate(db,T['Questions'],'QuestionID',ident,actor)

@admin.get('/academic/catalog')
def catalog():
    return {name:{'table':table,'key':key,'input_schema':model.model_json_schema()} for name,(table,key,model) in svc.RESOURCES.items()}

@public.get('/academic/{resource_name}')
def public_academic(resource_name:str,lang: str = Query("hy", pattern="^(hy|en)$"),p=Depends(pagination),db=Depends(get_db,scope="function")):
    t,key,_=svc.resource(resource_name)
    result=svc.page(db,select(t).where(t.c.IsActive==True),t.c[key],*p)
    if lang == "en" and resource_name == "chairs":
        from app.localization import department
        result["items"] = [{**item, "Name": department(item["Name"])} for item in result["items"]]
    return result

@admin.get('/academic/{resource_name}/export')
def academic_export(resource_name:str,q:str=Query('',max_length=150),active:bool|None=None,lecturer_id:int|None=Query(None,gt=0),p=Depends(pagination),db=Depends(get_db,scope="function")):
    t,key,_=svc.resource(resource_name);stmt=select(t)
    if lecturer_id is not None and resource_name=='courses':stmt=stmt.where(t.c.LecturerID==lecturer_id)
    if active is not None:stmt=stmt.where(t.c.IsActive==active)
    search=[c.contains(q,autoescape=True) for c in t.c if c.name in ['Name','ShortName','Code','GroupCode']]
    if q and search:stmt=stmt.where(or_(*search))
    return csv_response(svc.page(db,stmt,t.c[key],*p)['items'],resource_name+'.csv')

@admin.get('/academic/{resource_name}')
def academic_list(resource_name:str,q:str=Query('',max_length=150),active:bool|None=None,lecturer_id:int|None=Query(None,gt=0),p=Depends(pagination),db=Depends(get_db,scope="function")):
    t,key,_=svc.resource(resource_name);stmt=select(t)
    if lecturer_id is not None and resource_name=='courses':stmt=stmt.where(t.c.LecturerID==lecturer_id)
    if active is not None:stmt=stmt.where(t.c.IsActive==active)
    search=[c.contains(q,autoescape=True) for c in t.c if c.name in ['Name','ShortName','Code','GroupCode']]
    if q and search:stmt=stmt.where(or_(*search))
    return svc.page(db,stmt,t.c[key],*p)

def validated(model,payload):
    try:return model.model_validate(payload).model_dump()
    except ValidationError as exc:
        raise HTTPException(422,[{'field':'.'.join(map(str,e['loc'])),'message':e['msg']} for e in exc.errors()]) from None

@admin.post('/academic/{resource_name}',status_code=201)
def academic_add(resource_name:str,payload:dict=Body(...),db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    t,key,model=svc.resource(resource_name)
    return svc.create(db,t,key,validated(model,payload),actor)

@admin.put('/academic/{resource_name}/{ident}')
def academic_edit(resource_name:str,ident:int,payload:dict=Body(...),db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    t,key,model=svc.resource(resource_name)
    return svc.edit(db,t,key,ident,validated(model,payload),actor)

@admin.delete('/academic/{resource_name}/{ident}')
def academic_deactivate(resource_name:str,ident:int,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    t,key,_=svc.resource(resource_name)
    return svc.deactivate(db,t,key,ident,actor)

@admin.get('/semesters')
def semesters(db=Depends(get_db,scope="function")):
    return {'items':[dict(r) for r in db.execute(select(T['AcademicSemesters']).order_by(T['AcademicSemesters'].c.SemesterNumber)).mappings()]}

@admin.get('/student-options')
def students(q:str=Query('',max_length=100),p=Depends(pagination),db=Depends(get_db,scope="function")):
    t=T['Users'];stmt=select(t.c.UserID,t.c.FirstName,t.c.LastName,t.c.GroupID).where(t.c.Status=='Active')
    if q:stmt=stmt.where(or_(t.c.FirstName.contains(q,autoescape=True),t.c.LastName.contains(q,autoescape=True)))
    return svc.page(db,stmt,t.c.UserID,*p)

@admin.get('/student-courses/export')
def enrollment_export(q:str=Query('',max_length=150),user_id:int|None=Query(None,gt=0),course_id:int|None=Query(None,gt=0),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return csv_response(svc.page(db,svc.enrollment_query(q,user_id,course_id),T['StudentCourses'].c.StudentCourseID,*p)['items'],'student-courses.csv')

@admin.get('/student-courses')
def enrollments(q:str=Query('',max_length=150),user_id:int|None=Query(None,gt=0),course_id:int|None=Query(None,gt=0),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return svc.page(db,svc.enrollment_query(q,user_id,course_id),T['StudentCourses'].c.StudentCourseID,*p)

@admin.post('/student-courses',status_code=201)
def enroll(payload:StudentCourseInput,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.enroll(db,payload.model_dump(),actor)

@admin.delete('/student-courses/{ident}')
def unenroll(ident:int,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    t=T['StudentCourses'];svc.row(db,t,'StudentCourseID',ident)
    db.execute(t.delete().where(t.c.StudentCourseID==ident));svc.audit(db,actor,'Unlink',f'StudentCourses:{ident}')
    return {'deleted':ident}

@admin.put('/courses/{ident}/lecturer')
def assign_lecturer(ident:int,payload:Assignment,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.edit(db,T['Courses'],'CourseID',ident,payload.model_dump(),actor)

def comments_query(status,q):
    t=admin_ratings;stmt=select(t).where(t.c.Comment.is_not(None),t.c.Comment!='')
    if status:stmt=stmt.where(t.c.Status==status)
    if q:stmt=stmt.where(or_(t.c.Comment.contains(q,autoescape=True),t.c.LecturerName.contains(q,autoescape=True)))
    return stmt

@admin.get('/comments/export')
def comments_export(status:str|None=Query(None,pattern='^(Pending|Approved|Rejected)$'),q:str=Query('',max_length=150),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return csv_response(svc.page(db,comments_query(status,q),admin_ratings.c.RatingID,*p)['items'],'comments.csv')

@admin.get('/comments')
def comments(status:str|None=Query(None,pattern='^(Pending|Approved|Rejected)$'),q:str=Query('',max_length=150),p=Depends(pagination),db=Depends(get_db,scope="function")):
    return svc.page(db,comments_query(status,q),admin_ratings.c.RatingID,*p)

@admin.put('/comments/{ident}/moderation')
def moderate(ident:int,payload:Moderation,db=Depends(get_db,scope="function"),actor=Depends(get_actor)):
    return svc.moderate(db,ident,payload,actor)

@public.get('/lecturers/{ident}/comments')
def approved_comments(ident:int,p=Depends(pagination),db=Depends(get_db,scope="function")):
    from app.student2.tables import public_ratings
    t=public_ratings
    # View-ն ինքն է սահմանափակում Approved գրառումներով և չի ներառում UserID։
    svc.row(db,T['Lecturers'],'LecturerID',ident)
    active=db.execute(select(T['Lecturers'].c.IsActive).where(T['Lecturers'].c.LecturerID==ident)).scalar_one()
    if not active: raise HTTPException(404,'Դասախոսը չի գտնվել։')
    return svc.page(db,select(t).where(t.c.LecturerID==ident,t.c.Comment.is_not(None),t.c.Comment!=''),t.c.RatingID,*p)

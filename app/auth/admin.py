from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from sqlalchemy import select,func,or_,case
from app.student2.dependencies import get_db,get_actor
from app.student2.tables import TABLES as T, admin_ratings
from app.student2.service import page
from app.student2.router import pagination,csv_response
from app.auth.schemas import UserUpdate,RecoveryInput,StudentCreate
from app.auth.roster import check_group
from app.auth.academic import sync_student
from app.auth.crypto import hash_password
from app.auth import service as svc
from app.localization import person_display, transliterate

router=APIRouter(prefix='/api/admin',tags=['Accounts and dashboard'],dependencies=[Depends(get_actor)])

def users_query(q='',status=None,institute_id=None,faculty_id=None,chair_id=None,
                specialization_id=None,group_id=None,year=None):
    u,g,sp,ch,ins,fac,progress=[T[n] for n in
        ['Users','StudentGroups','Specializations','Chairs','Institutes','Faculty','StudentAcademicProgress']]
    # A single current semester per student; no guessed year from GroupCode.
    current=select(progress.c.UserID,func.max(progress.c.SemesterNumber).label('SemesterNumber')).where(
        progress.c.IsCurrent==True).group_by(progress.c.UserID).having(func.count()==1).subquery()
    semester=current.c.SemesterNumber
    study_year=case(*[(semester.between(n*2-1,n*2),n) for n in range(1,5)],else_=None)
    cols=[u.c[k] for k in ['UserID','FirstName','LastName','Email','IsEmailVerified','Status','LastLogin','GroupID']]
    stmt=select(*cols,g.c.GroupCode,g.c.EnrollmentYear,sp.c.SpecializationID,
        sp.c.Name.label('SpecializationName'),ch.c.ChairID,ch.c.Name.label('ChairName'),
        ch.c.InstituteID,ch.c.FacultyID,ins.c.Name.label('InstituteName'),fac.c.Name.label('FacultyName'),
        semester,study_year.label('StudyYear')).select_from(u.outerjoin(g,u.c.GroupID==g.c.GroupID)
        .outerjoin(sp,g.c.SpecializationID==sp.c.SpecializationID)
        .outerjoin(ch,sp.c.ChairID==ch.c.ChairID)
        .outerjoin(ins,ch.c.InstituteID==ins.c.InstituteID).outerjoin(fac,ch.c.FacultyID==fac.c.FacultyID)
        .outerjoin(current,u.c.UserID==current.c.UserID))
    if q:
        stmt=stmt.where(or_(*(u.c[k].contains(q,autoescape=True) for k in ['FirstName','LastName','Email']),
                            g.c.GroupCode.contains(q,autoescape=True)))
    if status:stmt=stmt.where(u.c.Status==status)
    for value,col in [(institute_id,ch.c.InstituteID),(faculty_id,ch.c.FacultyID),(chair_id,ch.c.ChairID),
                      (specialization_id,sp.c.SpecializationID),(group_id,g.c.GroupID),(year,study_year)]:
        if value is not None:stmt=stmt.where(col==value)
    return stmt


def user_filters(status:str|None=Query(None,pattern='^(Active|Suspended|Banned)$'),
                 institute_id:int|None=Query(None,gt=0),faculty_id:int|None=Query(None,gt=0),
                 chair_id:int|None=Query(None,gt=0),specialization_id:int|None=Query(None,gt=0),
                 group_id:int|None=Query(None,gt=0),year:int|None=Query(None,ge=1,le=4)):
    return dict(status=status,institute_id=institute_id,faculty_id=faculty_id,chair_id=chair_id,
                specialization_id=specialization_id,group_id=group_id,year=year)


@router.get('/users')
def users(q:str=Query('',max_length=150),filters=Depends(user_filters),
          p=Depends(pagination),db=Depends(get_db,scope='function'),
          lang:str=Query('hy',pattern='^(hy|en)$')):
    result=page(db,users_query(q,**filters),T['Users'].c.UserID,*p)
    result['items']=[person_display(item,lang) for item in result['items']]
    return result


@router.get('/users/export')
def export_users(q:str=Query('',max_length=150),filters=Depends(user_filters),
                 p=Depends(pagination),db=Depends(get_db,scope='function')):
    return csv_response(page(db,users_query(q,**filters),T['Users'].c.UserID,*p)['items'],'users.csv')


@router.post('/users',status_code=201)
def create_user(payload:StudentCreate,db=Depends(get_db,scope='function'),actor=Depends(get_actor)):
    u=T['Users']
    check_group(db,payload.GroupID)
    if db.execute(select(u.c.UserID).where(func.lower(u.c.Email)==payload.Email)).first():
        raise HTTPException(409,'This student account already exists.')
    ident=db.execute(u.insert().values(FirstName=payload.FirstName,LastName=payload.LastName,
        Email=payload.Email,GroupID=payload.GroupID,PasswordHash=hash_password(payload.Password),
        IsEmailVerified=True,Status='Active')).inserted_primary_key[0]
    academic_status=sync_student(db,ident)
    svc.audit(db,actor,'StudentCreated',f'Users:{ident}')
    svc.audit(db,actor,'AcademicSync',f'Users:{ident}:{academic_status}')
    item=dict(db.execute(users_query().where(u.c.UserID==ident)).mappings().one())
    return {'student':item,'academic_status':academic_status}


@router.put('/users/{ident}')
def update_user(ident:int,payload:UserUpdate,db=Depends(get_db,scope='function'),actor=Depends(get_actor)):
    u=T['Users']
    row=db.execute(select(u).where(u.c.UserID==ident)).mappings().first()
    if not row:raise HTTPException(404,'Student not found.')
    if payload.GroupID is not None and payload.GroupID!=row['GroupID']:
        check_group(db,payload.GroupID)
    values=payload.model_dump()
    # Group moves require academic-history reconciliation; the existing group remains the default.
    db.execute(u.update().where(u.c.UserID==ident).values(**values))
    if row['Status']!=payload.Status or row['GroupID']!=payload.GroupID:
        db.execute(svc.sessions.delete().where(svc.sessions.c.UserID==ident))
        if payload.Status!='Active':
            db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.UserID==ident).values(IsUsed=True))
    svc.audit(db,actor,'UserUpdated',f'Users:{ident}:{payload.Status}')
    return dict(db.execute(users_query().where(u.c.UserID==ident)).mappings().one())

@router.get('/activity-logs')
def logs(q:str=Query('',max_length=150),p=Depends(pagination),db=Depends(get_db,scope='function')):
    t=T['ActivityLogs'];stmt=select(t).order_by(t.c.LogID.desc())
    if q:stmt=stmt.where(or_(t.c.ActionType.contains(q,autoescape=True),t.c.Target.contains(q,autoescape=True)))
    return page(db,stmt,t.c.LogID,*p)

@router.get('/password-resets')
def reset_history(p=Depends(pagination),db=Depends(get_db,scope='function')):
    r=T['PasswordResets'];u=T['Users'];a=T['Admins']
    # Explicit safe projection: never return Code/token hashes.
    stmt=select(r.c.ResetID,r.c.UserID,r.c.AdminID,r.c.Purpose,r.c.Expiry,r.c.IsUsed,r.c.CreatedAt,
        func.coalesce(u.c.Email,a.c.Email).label('Email')).select_from(
        r.outerjoin(u,r.c.UserID==u.c.UserID).outerjoin(a,r.c.AdminID==a.c.AdminID)).order_by(r.c.ResetID.desc())
    return page(db,stmt,r.c.ResetID,*p)

@router.post('/password-resets')
def request_reset(payload:RecoveryInput,request:Request,db=Depends(get_db,scope='function'),actor=Depends(get_actor)):
    if not svc.throttle(db,request,'admin-reset',payload.Email,4):
        from app.auth.router import limited
        return limited()
    svc.recovery(db,payload)
    svc.audit(db,actor,'AdminRecoveryRequest',payload.Role)
    from app.auth.router import recovery_response
    return recovery_response(payload.Language)

@router.get('/dashboard')
def dashboard(db=Depends(get_db,scope='function'),actor=Depends(get_actor), lang: str = Query('hy', pattern='^(hy|en)$')):
    counts={name:db.execute(select(func.count()).select_from(T[table])).scalar_one()
        for name,table in [('users','Users'),('lecturers','Lecturers'),('ratings','Ratings')]}
    # Existing SQL view calculates per-rating scores; no duplicated score formula.
    ratings_view=admin_ratings
    avg=db.execute(select(func.avg(ratings_view.c.OverallScore)).where(ratings_view.c.Status=='Approved')).scalar()
    recent=[dict(r) for r in db.execute(select(T['ActivityLogs']).order_by(T['ActivityLogs'].c.LogID.desc()).limit(5)).mappings()]
    pending=[dict(r) for r in db.execute(select(ratings_view).where(ratings_view.c.Status=='Pending').order_by(ratings_view.c.RatingID).limit(5)).mappings()]
    a=T['Admins']
    profile=dict(db.execute(select(a.c.FirstName,a.c.LastName,a.c.Email).where(a.c.AdminID==actor.admin_id)).mappings().one())
    profile = person_display(profile, lang)
    for item in pending:
        item['DisplayLecturerName'] = transliterate(item.get('LecturerName')) if lang == 'en' else item.get('LecturerName')
    return {**counts,'average_score':float(avg) if avg is not None else None,'recent_activity':recent,'pending_reviews':pending,'admin':profile}

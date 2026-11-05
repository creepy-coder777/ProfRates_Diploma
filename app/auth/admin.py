from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from sqlalchemy import select,func,or_
from app.student2.dependencies import get_db,get_actor
from app.student2.tables import TABLES as T, admin_ratings
from app.student2.service import page
from app.student2.router import pagination,csv_response
from app.auth.schemas import UserUpdate,RecoveryInput,RosterInput,RosterState
from app.auth.roster import roster, check_group
from app.auth import service as svc
from app.localization import person_display, transliterate

router=APIRouter(prefix='/api/admin',tags=['Accounts and dashboard'],dependencies=[Depends(get_actor)])

def users_query(q='',status=None):
    u=T['Users'];g=T['StudentGroups']
    cols=[u.c[k] for k in ['UserID','FirstName','LastName','Email','IsEmailVerified','Status','LastLogin','GroupID']]
    stmt=select(*cols,g.c.GroupCode).select_from(u.outerjoin(g,u.c.GroupID==g.c.GroupID))
    if q:
        stmt=stmt.where(or_(*(u.c[k].contains(q,autoescape=True) for k in ['FirstName','LastName','Email'])))
    if status:stmt=stmt.where(u.c.Status==status)
    return stmt

@router.get('/users')
def users(q:str=Query('',max_length=150),status:str|None=Query(None,pattern='^(Active|Suspended|Banned)$'),
          p=Depends(pagination),db=Depends(get_db,scope='function'),
          lang: str = Query('hy', pattern='^(hy|en)$')):
    result = page(db,users_query(q,status),T['Users'].c.UserID,*p)
    result['items'] = [person_display(item, lang) for item in result['items']]
    return result

@router.get('/users/export')
def export_users(q:str=Query('',max_length=150),p=Depends(pagination),db=Depends(get_db,scope='function')):
    return csv_response(page(db,users_query(q),T['Users'].c.UserID,*p)['items'],'users.csv')

@router.put('/users/{ident}')
def update_user(ident:int,payload:UserUpdate,db=Depends(get_db,scope='function'),actor=Depends(get_actor)):
    u=T['Users']
    row=db.execute(select(u).where(u.c.UserID==ident)).mappings().first()
    if not row:raise HTTPException(404,'Student not found.')
    if payload.GroupID is not None:
        g=T['StudentGroups']
        if not db.execute(select(g.c.GroupID).where(g.c.GroupID==payload.GroupID,g.c.IsActive==True)).first():
            raise HTTPException(422,'Choose an active group.')
    db.execute(u.update().where(u.c.UserID==ident).values(**payload.model_dump()))
    if row['Status']!=payload.Status:
        db.execute(svc.sessions.delete().where(svc.sessions.c.UserID==ident))
        if payload.Status!='Active':
            db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.UserID==ident).values(IsUsed=True))
    roster_values = {'FirstName':payload.FirstName, 'LastName':payload.LastName}
    if payload.GroupID is not None: roster_values['GroupID'] = payload.GroupID
    db.execute(roster.update().where(roster.c.UserID == ident).values(**roster_values))
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
    avg=db.execute(select(func.avg(ratings_view.c.OverallScore))).scalar()
    recent=[dict(r) for r in db.execute(select(T['ActivityLogs']).order_by(T['ActivityLogs'].c.LogID.desc()).limit(5)).mappings()]
    pending=[dict(r) for r in db.execute(select(ratings_view).where(ratings_view.c.Status=='Pending').order_by(ratings_view.c.RatingID).limit(5)).mappings()]
    a=T['Admins']
    profile=dict(db.execute(select(a.c.FirstName,a.c.LastName,a.c.Email).where(a.c.AdminID==actor.admin_id)).mappings().one())
    profile = person_display(profile, lang)
    for item in pending:
        item['DisplayLecturerName'] = transliterate(item.get('LecturerName')) if lang == 'en' else item.get('LecturerName')
    return {**counts,'average_score':float(avg) if avg is not None else None,'recent_activity':recent,'pending_reviews':pending,'admin':profile}


@router.get('/student-roster')
def roster_list(q: str = Query('', max_length=150), p=Depends(pagination),
                db=Depends(get_db, scope='function'), registered: bool | None = None,
                lang: str = Query('hy', pattern='^(hy|en)$')):
    g = T['StudentGroups']
    statement = select(roster, g.c.GroupCode).select_from(roster.join(g, g.c.GroupID == roster.c.GroupID))
    if q:
        statement = statement.where(or_(*(roster.c[n].contains(q, autoescape=True)
                                          for n in ['Email','FirstName','LastName'])))
    if registered is not None:
        statement = statement.where(roster.c.UserID.is_not(None) if registered else roster.c.UserID.is_(None))
    result = page(db, statement, roster.c.Email, *p)
    result['items'] = [person_display(item, lang) for item in result['items']]
    return result


@router.post('/student-roster', status_code=201)
def roster_add(payload: RosterInput, actor=Depends(get_actor), db=Depends(get_db, scope='function')):
    check_group(db, payload.GroupID)
    if db.execute(select(roster.c.Email).where(roster.c.Email == payload.Email)).first():
        raise HTTPException(409, 'This email is already in the registration roster.')
    if db.execute(select(T['Users'].c.UserID).where(func.lower(T['Users'].c.Email) == payload.Email)).first():
        raise HTTPException(409, 'This account already exists. Use account management or password recovery.')
    db.execute(roster.insert().values(**payload.model_dump(), IsActive=True, UserID=None))
    svc.audit(db, actor, 'RosterAdded', 'StudentRoster:'+payload.Email)
    return payload.model_dump()


@router.put('/student-roster/{email}')
def roster_state(email: str, payload: RosterState, actor=Depends(get_actor),
                 db=Depends(get_db, scope='function')):
    email = email.strip().lower()
    item = db.execute(select(roster).where(roster.c.Email == email)).mappings().first()
    if item is None:
        raise HTTPException(404, 'Roster entry not found.')
    db.execute(roster.update().where(roster.c.Email == email).values(IsActive=payload.IsActive))
    if item['UserID'] and not payload.IsActive:
        # Suspending access preserves the account, ratings, and study history.
        db.execute(T['Users'].update().where(T['Users'].c.UserID == item['UserID'],
            T['Users'].c.Status == 'Active').values(Status='Suspended'))
        db.execute(svc.sessions.delete().where(svc.sessions.c.UserID == item['UserID']))
        db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.UserID == item['UserID']).values(IsUsed=True))
    svc.audit(db, actor, 'RosterStateChanged', 'StudentRoster:'+email)
    return {'Email': email, 'IsActive': payload.IsActive}

from datetime import datetime
from fastapi import HTTPException
from sqlalchemy import select, func, or_, and_, exists
from app.student2.tables import TABLES as T, summary, admin_ratings
from app.student2.schemas import UnitInput, ChairInput, SpecializationInput, GroupInput, CourseInput

RESOURCES = {
    'institutes': ('Institutes','InstituteID',UnitInput),
    'faculties': ('Faculty','FacultyID',UnitInput),
    'chairs': ('Chairs','ChairID',ChairInput),
    'specializations': ('Specializations','SpecializationID',SpecializationInput),
    'groups': ('StudentGroups','GroupID',GroupInput),
    'courses': ('Courses','CourseID',CourseInput),
}
REFERENCES = {'InstituteID':('Institutes','InstituteID'), 'FacultyID':('Faculty','FacultyID'),
 'ChairID':('Chairs','ChairID'), 'SpecializationID':('Specializations','SpecializationID'),
 'LecturerID':('Lecturers','LecturerID'), 'CurriculumSemesterNumber':('AcademicSemesters','SemesterNumber'),
 'CourseID':('Courses','CourseID'),'UserID':('Users','UserID')}

def row(db, table, key, ident):
    result = db.execute(select(table).where(table.c[key] == ident)).mappings().first()
    if result is None:
        raise HTTPException(404, 'Գրառումը չի գտնվել։')
    return dict(result)

def resource(name):
    if name not in RESOURCES: raise HTTPException(404, 'Անհայտ բաժին։')
    table,key,model = RESOURCES[name]
    return T[table],key,model

def audit(db, actor, action, target):
    # Ընդհանուր audit ծառայությունը տրամադրելու դեպքում օգտագործվում է միայն այն։
    from app.config import get_settings
    from importlib import import_module
    provider=get_settings().audit_provider
    if provider:
        try:
            module,name=provider.split(':',1)
            getattr(import_module(module),name)(db,actor,action,target)
        except Exception:
            raise HTTPException(503,'Գործողությունների մատյանի ծառայությունը հասանելի չէ։') from None
        return
    db.execute(T['ActivityLogs'].insert().values(AdminID=actor.admin_id,UserID=actor.user_id,
        ActionType=action,Target=target,Status='Success',CreatedAt=datetime.now()))

def validate_references(db, values):
    for key,(table,pk) in REFERENCES.items():
        if values.get(key) is not None:
            parent=row(db,T[table],pk,values[key])
            if 'IsActive' in parent and not parent['IsActive']:
                raise HTTPException(409,'Կապվող գրառումը ապաակտիվացված է։')
            if table=='Users' and parent['Status']!='Active':
                raise HTTPException(409,'Ուսանողի հաշիվն ակտիվ չէ։')

def create(db, table, key, values, actor):
    validate_references(db,values)
    result=db.execute(table.insert().values(**values))
    ident=result.inserted_primary_key[0]
    audit(db,actor,'Create',f'{table.name}:{ident}')
    return row(db,table,key,ident)

def edit(db, table, key, ident, values, actor):
    old=row(db,table,key,ident)
    # Անփոփոխ կապերը թույլատրվում են նույնիսկ եթե ծնողը հետագայում ապաակտիվացվել է։
    validate_references(db,{k:v for k,v in values.items() if old.get(k)!=v})
    if table.name=='Courses' and old['LecturerID']!=values.get('LecturerID',old['LecturerID']):
        if db.execute(select(T['Ratings'].c.RatingID).where(T['Ratings'].c.CourseID==ident).limit(1)).first():
            raise HTTPException(409,'Առարկան արդեն գնահատումներ ունի։ Նոր դասախոսի համար ստեղծեք առանձին առարկայի գրառում՝ պատմությունը պահպանելու համար։')
    db.execute(table.update().where(table.c[key]==ident).values(**values))
    audit(db,actor,'Update',f'{table.name}:{ident}')
    return row(db,table,key,ident)

def deactivate(db, table, key, ident, actor):
    old=row(db,table,key,ident)
    if old['IsActive']:
        db.execute(table.update().where(table.c[key]==ident).values(IsActive=False))
        audit(db,actor,'Deactivate',f'{table.name}:{ident}')
    return row(db,table,key,ident)

def page(db, statement, key, page_no, page_size):
    total=db.execute(select(func.count()).select_from(statement.order_by(None).subquery())).scalar_one()
    # Keep the requested ordering; append the stable key only when absent.
    has_key = any(getattr(order, 'element', order).compare(key) for order in statement._order_by_clauses)
    ordered = statement if has_key else statement.order_by(key)
    items=[dict(r) for r in db.execute(ordered.offset((page_no-1)*page_size).limit(page_size)).mappings()]
    return {'items':items,'total':total,'page':page_no,'page_size':page_size}

def lecturer_search_aliases(db, query):
    """Match Latin queries against the same transliteration used for display."""
    if not any("a" <= char.lower() <= "z" for char in query):
        return {}
    from app.localization import transliterate
    fields = ("FirstName", "MiddleName", "LastName", "Title")
    table = T["Lecturers"]
    words = query.split()
    matches = {word: [] for word in words}
    # Resolve aliases before pagination; retain SQL filters and stable ordering.
    for item in db.execute(select(table.c.LecturerID, *(table.c[n] for n in fields))).mappings():
        aliases = [transliterate(item[n] or "").casefold() for n in fields]
        for word in words:
            if any(word.casefold() in alias for alias in aliases):
                matches[word].append(item["LecturerID"])
    return matches


def lecturer_query(q='', active=True, chair_id=None, institute_id=None, faculty_id=None, specialization_id=None, course_id=None, sort="id", alias_matches=None):
    l=T['Lecturers']; co=T['Courses']; sp=T['Specializations']; ch=T['Chairs']
    statement=select(*l.c,summary.c.TotalRatings,summary.c.AverageScore).select_from(l.outerjoin(summary,l.c.LecturerID==summary.c.LecturerID))
    if active is not None: statement=statement.where(l.c.IsActive==active)
    if q:
        for word in q.split():
            conditions = [l.c[n].contains(word, autoescape=True)
                          for n in ['FirstName','MiddleName','LastName','Title']]
            aliases = (alias_matches or {}).get(word, [])
            if aliases:
                conditions.append(l.c.LecturerID.in_(aliases))
            statement = statement.where(or_(*conditions))
    filters=[co.c.LecturerID==l.c.LecturerID,co.c.IsActive==True,sp.c.IsActive==True,ch.c.IsActive==True]
    for value,col in [(chair_id,ch.c.ChairID),(institute_id,ch.c.InstituteID),(faculty_id,ch.c.FacultyID),
                      (specialization_id,sp.c.SpecializationID),(course_id,co.c.CourseID)]:
        if value is not None: filters.append(col==value)
    if any(v is not None for v in [chair_id,institute_id,faculty_id,specialization_id,course_id]):
        statement=statement.where(exists(select(1).select_from(co.join(sp,co.c.SpecializationID==sp.c.SpecializationID).join(ch,sp.c.ChairID==ch.c.ChairID)).where(*filters)))
    order={"highest":summary.c.AverageScore.desc(),"lowest":summary.c.AverageScore.asc(),"a-z":l.c.FirstName.asc(),"z-a":l.c.FirstName.desc(),"id":l.c.LecturerID.asc()}
    return statement.order_by(order[sort])

def lecturer_departments(db, items):
    if not items: return items
    co=T['Courses']; sp=T['Specializations']; ch=T['Chairs']
    rows=db.execute(select(co.c.LecturerID,ch.c.Name).select_from(co.join(sp,co.c.SpecializationID==sp.c.SpecializationID).join(ch,sp.c.ChairID==ch.c.ChairID)).where(co.c.LecturerID.in_([i['LecturerID'] for i in items]),co.c.IsActive==True)).all()
    for item in items: item['Chairs']=sorted({r.Name for r in rows if r.LecturerID==item['LecturerID']})
    return items

def question_edit(db, ident, values, actor):
    table=T['Questions']; old=row(db,table,'QuestionID',ident)
    semantic=old['Text']!=values['Text'] or old['Category']!=values['Category']
    answered=db.execute(select(T['RatingAnswers'].c.AnswerID).where(T['RatingAnswers'].c.QuestionID==ident).limit(1)).first()
    if semantic and answered:
        # Նոր տարբերակ՝ միայն առկա աղյուսակի նոր գրառում։ Հին պատասխանների FK-ները մնում են անփոփոխ։
        deactivate(db,table,'QuestionID',ident,actor)
        result=create(db,table,'QuestionID',values,actor)
        return {'question':result,'replaced_question_id':ident}
    return {'question':edit(db,table,'QuestionID',ident,values,actor),'replaced_question_id':None}

def enroll(db, values, actor):
    validate_references(db,values)
    table=T['StudentCourses']
    if db.execute(select(table.c.StudentCourseID).where(table.c.UserID==values['UserID'],table.c.CourseID==values['CourseID'])).first():
        raise HTTPException(409,'Ուսանողն արդեն կապված է առարկային։')
    return create(db,table,'StudentCourseID',{**values,'EnrolledAt':datetime.now()},actor)

def moderate(db, ident, payload, actor):
    table=T['Ratings']; old=row(db,table,'RatingID',ident)
    if old['Status']!=payload.expected_status:
        raise HTTPException(409,'Կարգավիճակը փոխվել է։ Թարմացրեք էջը։')
    if old['Status']!=payload.status:
        result=db.execute(table.update().where(table.c.RatingID==ident,table.c.Status==payload.expected_status).values(
            Status=payload.status,ApprovedByAdminID=actor.admin_id,UpdatedAt=datetime.now()))
        if result.rowcount!=1: raise HTTPException(409,'Գրառումը փոխվել է։')
        audit(db,actor,'Moderate',f'Ratings:{ident}:{payload.status}')
    # Ամփոփումը հաշվարկվում է առկա vwLecturerRatingSummary view-ով։ Այստեղ վերահաշվարկ չկա։
    return {'RatingID':ident,'Status':payload.status,'rating_source':'dbo.vwLecturerRatingSummary'}


def enrollment_query(q='', user_id=None, course_id=None):
    sc=T['StudentCourses'];u=T['Users'];g=T['StudentGroups'];co=T['Courses']
    statement=select(*sc.c,u.c.FirstName.label('StudentFirstName'),u.c.LastName.label('StudentLastName'),
        g.c.GroupCode,co.c.Name.label('CourseName')).select_from(
        sc.join(u,sc.c.UserID==u.c.UserID).join(co,sc.c.CourseID==co.c.CourseID).outerjoin(g,u.c.GroupID==g.c.GroupID))
    if user_id is not None:statement=statement.where(sc.c.UserID==user_id)
    if course_id is not None:statement=statement.where(sc.c.CourseID==course_id)
    for word in q.split():
        statement=statement.where(or_(*(c.contains(word,autoescape=True) for c in
            [u.c.FirstName,u.c.LastName,g.c.GroupCode,co.c.Name])))
    return statement

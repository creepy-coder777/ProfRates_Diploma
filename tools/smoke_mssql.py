"""Local service/database smoke test. Never adds an HTTP authentication bypass.
Default: read-only verification. Writes require --write-rollback and use one rollback-only transaction.
"""
import argparse,json,uuid
from datetime import datetime
from pathlib import Path
from fastapi import HTTPException
from sqlalchemy import select,func
from app.database import get_engine
from app.config import get_settings
from app.security import Principal
from app.student2.tables import TABLES as T,summary,public_ratings
from app.student2 import service as svc
from app.student2.schemas import Moderation,LecturerInput,QuestionInput
from tools.verify_schema import inspect_database,compare_metadata,CONTRACT_PATH


def expect_http(status,callback):
    try:callback()
    except HTTPException as exc:
        if exc.status_code==status:return
        raise
    raise AssertionError('Expected HTTP status '+str(status))


def exercise(db,admin_id,mark,step):
    """New fixtures only. Caller owns transaction and MUST roll it back."""
    if not db.execute(select(T['Admins'].c.AdminID).where(T['Admins'].c.AdminID==admin_id)).first():
        raise ValueError('AdminID does not exist')
    actor=Principal(None,True,admin_id);created=[]
    def create(table,key,values):
        result=svc.create(db,T[table],key,values,actor);created.append((table,key,result[key]));return result[key]
    def check(value,message):
        if not value:raise AssertionError(message)
    first=LecturerInput(FirstName=mark,LastName='Test').model_dump()
    lid=create('Lecturers','LecturerID',{**first,'ViewCount':0})
    second=create('Lecturers','LecturerID',{**first,'FirstName':mark+'B','ViewCount':0})
    svc.edit(db,T['Lecturers'],'LecturerID',lid,{**first,'Title':'smoke-test'},actor)
    check(svc.row(db,T['Lecturers'],'LecturerID',lid)['Title']=='smoke-test','lecturer edit')
    found=svc.page(db,svc.lecturer_query(q=mark),T['Lecturers'].c.LecturerID,1,20)
    check(any(r['LecturerID']==lid for r in found['items']),'lecturer search');step('lecturer_create_edit_search')
    institute=create('Institutes','InstituteID',{'Name':mark,'ShortName':mark,'IsActive':True})
    faculty=create('Faculty','FacultyID',{'Name':mark,'ShortName':mark,'IsActive':True})
    chair=create('Chairs','ChairID',{'Name':mark,'ShortName':mark,'InstituteID':institute,'FacultyID':None,'IsActive':True})
    spec=create('Specializations','SpecializationID',{'ChairID':chair,'Name':mark,'Code':mark,'IsActive':True})
    group=create('StudentGroups','GroupID',{'GroupCode':mark,'SpecializationID':spec,'EnrollmentYear':2026,'IsActive':True})
    semester=db.execute(select(T['AcademicSemesters'].c.SemesterNumber).order_by(T['AcademicSemesters'].c.SemesterNumber)).scalar()
    if semester is None:raise ValueError('An existing AcademicSemesters row is required')
    course=create('Courses','CourseID',{'Name':mark,'SpecializationID':spec,'LecturerID':lid,'CurriculumSemesterNumber':semester,'IsActive':True})
    svc.edit(db,T['Courses'],'CourseID',course,{'LecturerID':second},actor)
    svc.edit(db,T['Courses'],'CourseID',course,{'LecturerID':lid},actor)
    for table,key,ident in [('Institutes','InstituteID',institute),('Faculty','FacultyID',faculty),('Chairs','ChairID',chair),('Specializations','SpecializationID',spec)]:
        svc.edit(db,T[table],key,ident,{'Name':mark+' edited'},actor)
    svc.edit(db,T['StudentGroups'],'GroupID',group,{'EnrollmentYear':2025},actor)
    check(svc.page(db,svc.lecturer_query(q=mark,chair_id=chair),T['Lecturers'].c.LecturerID,1,20)['total']==1,'chair filter')
    step('academic_create_edit_and_lecturer_course_link')
    # Unusable password fixture only; this does not implement registration and cannot be used to sign in.
    uid=db.execute(T['Users'].insert().values(FirstName=mark,LastName='Fixture',Email=mark+'@example.invalid',
        PasswordHash='!unusable!'+uuid.uuid4().hex,IsEmailVerified=False,Status='Active',GroupID=group)).inserted_primary_key[0]
    created.append(('Users','UserID',uid))
    enrollment=svc.enroll(db,{'UserID':uid,'CourseID':course},actor)
    created.append(('StudentCourses','StudentCourseID',enrollment['StudentCourseID']))
    check(svc.page(db,svc.enrollment_query(q=mark,user_id=uid),T['StudentCourses'].c.StudentCourseID,1,20)['total']==1,'enrollment search')
    expect_http(409,lambda:svc.enroll(db,{'UserID':uid,'CourseID':course},actor));step('student_course_link_search_duplicate')
    qvalues=QuestionInput(Text=mark,Category=mark,SortOrder=999000,IsActive=True).model_dump()
    qid=create('Questions','QuestionID',qvalues)
    rid=db.execute(T['Ratings'].insert().values(UserID=uid,LecturerID=lid,CourseID=course,Comment=mark,Status='Pending',
        Likes=0,Dislikes=0,CreatedAt=datetime.now(),UpdatedAt=datetime.now())).inserted_primary_key[0]
    created.append(('Ratings','RatingID',rid))
    aid=db.execute(T['RatingAnswers'].insert().values(RatingID=rid,QuestionID=qid,Score=5)).inserted_primary_key[0]
    created.append(('RatingAnswers','AnswerID',aid))
    result=svc.question_edit(db,qid,{**qvalues,'Text':mark+' revised'},actor)
    newq=result['question']['QuestionID'];created.append(('Questions','QuestionID',newq))
    check(newq!=qid and not svc.row(db,T['Questions'],'QuestionID',qid)['IsActive'],'question new version')
    check(svc.row(db,T['RatingAnswers'],'AnswerID',aid)['QuestionID']==qid,'answer history')
    check(svc.row(db,T['Questions'],'QuestionID',qid)['Text']==mark,'original text preserved');step('question_version_and_answer_history')
    svc.moderate(db,rid,Moderation(status='Approved',expected_status='Pending'),actor)
    def totals():return db.execute(select(summary.c.TotalRatings).where(summary.c.LecturerID==lid)).scalar_one()
    check(totals()==1,'approved summary view')
    check(db.execute(select(func.count()).select_from(public_ratings).where(public_ratings.c.RatingID==rid)).scalar_one()==1,'approved public view')
    from app.student3.reactions import state
    student_actor = Principal(uid, False)
    liked = state(db, student_actor, rid, 1, True)
    check(liked['Likes'] == 1 and liked['Dislikes'] == 0, 'SQL reaction insert trigger')
    check(state(db, student_actor, rid, 1, True)['Likes'] == 1, 'idempotent SQL reaction')
    switched = state(db, student_actor, rid, -1, True)
    check(switched['Likes'] == 0 and switched['Dislikes'] == 1, 'SQL reaction update trigger')
    cleared = state(db, student_actor, rid, None, True)
    check(cleared['Likes'] == 0 and cleared['Dislikes'] == 0, 'SQL reaction delete trigger')
    step('reaction_sql_trigger_insert_switch_clear')
    log_count=db.execute(select(func.count()).select_from(T['ActivityLogs'])).scalar_one()
    svc.moderate(db,rid,Moderation(status='Approved',expected_status='Approved'),actor)
    check(db.execute(select(func.count()).select_from(T['ActivityLogs'])).scalar_one()==log_count,'idempotent moderation')
    expect_http(409,lambda:svc.edit(db,T['Courses'],'CourseID',course,{'LecturerID':second},actor))
    svc.moderate(db,rid,Moderation(status='Rejected',expected_status='Approved'),actor)
    check(totals()==0,'rejected rating excluded from numeric summary')
    check(db.execute(select(func.count()).select_from(public_ratings).where(public_ratings.c.RatingID==rid)).scalar_one()==0,'rejected public view')
    step('approve_reject_live_views_idempotency')
    db.execute(T['StudentCourses'].delete().where(T['StudentCourses'].c.StudentCourseID==enrollment['StudentCourseID']))
    svc.audit(db,actor,'Unlink',f"StudentCourses:{enrollment['StudentCourseID']}")
    for table,key,ident in [('Lecturers','LecturerID',lid),('Courses','CourseID',course),('StudentGroups','GroupID',group),('Specializations','SpecializationID',spec),('Chairs','ChairID',chair),('Faculty','FacultyID',faculty),('Institutes','InstituteID',institute),('Questions','QuestionID',newq)]:
        check(not svc.deactivate(db,T[table],key,ident,actor)['IsActive'],'deactivate '+table)
    step('deactivate_only_new_records')
    return created


def main(argv=None):
    parser=argparse.ArgumentParser(description='Local MSSQL checks. All fixture DML is rolled back; IDENTITY gaps may remain.')
    parser.add_argument('--write-rollback',action='store_true',help='Explicitly run fixture writes, then ROLLBACK')
    parser.add_argument('--admin-id',type=int,help='Existing AdminID for test audit references, not an HTTP login')
    parser.add_argument('--reviewed-behavior',action='store_true',help='Only after reviewing view differences and enabled triggers for side effects')
    parser.add_argument('--output',type=Path,default=Path('exports/mssql_smoke_report.json'))
    args=parser.parse_args(argv);report={'status':'not_run','authentication':'NOT_TESTED: local DB/service check, not authenticated API test',
        'committed_api_persistence':'NOT_TESTED','backup_correspondence':'UNCONFIRMED','steps':[],'fixture_changes':'not_started'}
    try:
        engine=get_engine();snapshot=inspect_database(engine)
        structure=compare_metadata(snapshot,json.loads(CONTRACT_PATH.read_text()))
        report['structural_status']=structure['structural_status'];report['database']=structure['database']
        report['view_definition_comparison']=structure['view_definition_comparison'];report['triggers']=structure['triggers']
        if structure['errors']:raise ValueError('Schema does not match: run tools.verify_schema first')
        if not args.write_rollback:
            report['status']='read_only_complete';print('Կառուցվածքն ընթերցված է. գրառումներ չեն ստեղծվել։');return 0
        if not args.admin_id or args.admin_id<1:raise ValueError('--admin-id is required for fixture writes')
        if get_settings().audit_provider:raise ValueError('External AUDIT_PROVIDER is not allowed in rollback smoke test; review its side effects separately')
        behavior_warning=any(not t['disabled']for t in structure['triggers'])or any(s!='text_match'for s in structure['view_definition_comparison'].values())
        if behavior_warning and not args.reviewed_behavior:raise ValueError('Review views/triggers before --reviewed-behavior')
        mark='S2TEST_'+uuid.uuid4().hex[:10];report['run_id']=mark
        with engine.connect().execution_options(isolation_level='SERIALIZABLE') as db:
            transaction=db.begin()
            try:
                report['fixture_changes']='in_transaction'
                created=exercise(db,args.admin_id,mark,lambda name:report['steps'].append({'name':name,'status':'passed'}))
            finally:
                transaction.rollback();report['fixture_changes']='ROLLBACK completed; IDENTITY gaps may remain'
        # A new connection must not see any of the fixture rows.
        with engine.connect() as db:
            for table,key,ident in created:
                if db.execute(select(T[table].c[key]).where(T[table].c[key]==ident)).first():raise AssertionError('Fixture row survived rollback')
        report['status']='passed_rollback_only';print('MSSQL փորձարկումը հաջող է։ Փորձնական տվյալները հետ են գլորվել։')
        print('Նույնականացումն ու commit-ից հետո UI պահպանումը այս գործիքը չեն ստուգում։');return 0
    except Exception as exc:
        report['status']='failed';report['error_type']=type(exc).__name__
        # No DBAPI messages, SQL parameters, tokens or connection strings in output.
        if isinstance(exc,ValueError):report['reason']=str(exc)
        print('Փորձարկումը չի ավարտվել. '+type(exc).__name__)
        if 'reason'in report:print(report['reason'])
        return 1
    finally:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2))
        print('Հաշվետվություն՝ '+str(args.output))
if __name__=='__main__':raise SystemExit(main())

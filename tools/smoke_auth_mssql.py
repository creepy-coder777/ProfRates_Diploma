"""Explicit opt-in test writes to the existing local SQL Server. Never reseeds it."""
import argparse,json,getpass
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from datetime import timedelta
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.config import get_settings,ROOT
from app.database import get_engine
from app.student2.tables import TABLES as T
from app.auth import service as svc
from app.auth.crypto import new_token

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--confirm-test-writes',action='store_true',required=True)
    p.add_argument('--admin-email',help='Optional: exercise an existing admin account using a prompted password')
    args=p.parse_args()
    s=get_settings()
    if s.app_env!='development' or s.mail_backend!='local':
        raise SystemExit('This demonstration requires development + local mail.')
    engine=get_engine()
    if engine.dialect.name!='mssql':raise SystemExit('Real SQL Server required.')
    email='acceptance.'+new_token()[:12].lower()+'@polytechnic.am'
    password=new_token();new_password=new_token()
    user_id=None;checks=[]
    def check(condition,label):
        checks.append((label,bool(condition)))
        if not condition:raise AssertionError(label)
        print('PASS: '+label)
    def mail_token(purpose):
        folder=Path(s.local_mail_dir)
        if not folder.is_absolute():folder=ROOT/folder
        files=sorted(folder.glob('*.json'),key=lambda x:x.stat().st_mtime,reverse=True)
        for f in files:
            m=json.loads(f.read_text(encoding='utf-8'))
            if m['recipient']==email and m['purpose']==purpose:
                return parse_qs(urlsplit(m['link']).fragment)['token'][0]
        raise AssertionError('Private test message missing')
    try:
        with engine.connect() as db:
            g,sp,ch=T['StudentGroups'],T['Specializations'],T['Chairs']
            group=db.execute(select(g.c.GroupID,ch.c.ChairID).select_from(g.join(sp,g.c.SpecializationID==sp.c.SpecializationID).join(ch,sp.c.ChairID==ch.c.ChairID)).where(g.c.IsActive==True,sp.c.IsActive==True,ch.c.IsActive==True).limit(1)).mappings().one()
        with TestClient(app) as c:
            c.headers['X-ProfRates-Request']='1'
            def post(path,payload):
                csrf=c.cookies.get('pr_csrf')
                return c.post(path,json=payload,headers={'X-CSRF-Token':csrf} if csrf else {})
            with engine.begin() as db:
                db.execute(T['StudentRoster'].insert().values(Email=email,FirstName='Acceptance',LastName='Test',GroupID=group['GroupID'],IsActive=True,UserID=None))
                svc.audit(db,None,'AcceptanceRosterSeed','StudentRoster:'+email)
            r=post('/api/auth/register',dict(Email=email,Password=password))
            check(r.status_code==201,'registration on SQL Server')
            with engine.connect() as db:
                user_id=db.execute(select(T['Users'].c.UserID).where(T['Users'].c.Email==email)).scalar_one()
            verify=mail_token('verify')
            check(post('/api/auth/verify-email',{'Token':verify}).status_code==200,'email verification')
            check(post('/api/auth/verify-email',{'Token':verify}).status_code==400,'verification replay rejected')
            check(post('/api/auth/login',{'Email':email,'Password':password}).status_code==200,'student login')
            check(c.get('/api/admin/users').status_code==403,'student cannot access administrator API')
            check(post('/api/auth/logout',{}).status_code==200,'logout')
            check(c.get('/api/auth/session').status_code==401,'logged-out session rejected')
            a=post('/api/auth/forgot-password',{'Email':email})
            b=post('/api/auth/forgot-password',{'Email':'unknown.'+new_token()[:10]+'@polytechnic.am'})
            check(a.status_code==b.status_code==200 and a.json()==b.json(),'non-enumerating recovery')
            reset=mail_token('reset')
            check(post('/api/auth/reset-password',{'Token':'x'*43,'Password':new_password}).status_code==400,'invalid token rejected')
            check(post('/api/auth/reset-password',{'Token':reset,'Password':new_password}).status_code==200,'reset succeeds')
            check(post('/api/auth/reset-password',{'Token':reset,'Password':new_password}).status_code==400,'reset replay rejected')
            check(post('/api/auth/login',{'Email':email,'Password':password}).status_code==401,'old password rejected')
            check(post('/api/auth/login',{'Email':email,'Password':new_password}).status_code==200,'new password accepted')
            post('/api/auth/forgot-password',{'Email':email})
            expired=mail_token('reset')
            with engine.begin() as db:
                db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.UserID==user_id,T['PasswordResets'].c.Purpose=='reset').values(Expiry=svc.now()-timedelta(seconds=1)))
            check(post('/api/auth/reset-password',{'Token':expired,'Password':password}).status_code==400,'expired token rejected')
            post('/api/auth/logout',{})
            if args.admin_email:
                secret=getpass.getpass('Existing administrator password: ')
                check(post('/api/auth/admin/login',{'Email':args.admin_email,'Password':secret}).status_code==200,'administrator login')
                for endpoint in ['dashboard','users','activity-logs','password-resets','lecturers','questions']:
                    check(c.get('/api/admin/'+endpoint).status_code==200,'admin '+endpoint)
                post('/api/auth/logout',{})
        print('SQL Server checks completed; test account will be suspended, audit retained.')
        return 0
    except Exception:
        print('FAILED: check configuration/schema; no credentials or tokens displayed.')
        return 1
    finally:
        if user_id is not None:
            with engine.begin() as db:
                db.execute(T['Users'].update().where(T['Users'].c.UserID==user_id).values(Status='Suspended'))
                db.execute(svc.sessions.delete().where(svc.sessions.c.UserID==user_id))
                db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.UserID==user_id).values(IsUsed=True))
                svc.audit(db,None,'AcceptanceCleanup',f'Users:{user_id}')
        with engine.begin() as db:
            db.execute(T['StudentRoster'].update().where(T['StudentRoster'].c.Email==email).values(IsActive=False))
        # Local messages contain test bearer links. Remove only this test's messages.
        folder=Path(s.local_mail_dir)
        if not folder.is_absolute():folder=ROOT/folder
        for file in folder.glob('*.json'):
            if json.loads(file.read_text(encoding='utf-8')).get('recipient')==email:file.unlink()
if __name__=='__main__':raise SystemExit(main())

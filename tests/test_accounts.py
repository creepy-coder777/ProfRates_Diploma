"""Real FastAPI handlers and database-backed auth; SQLite is NOT a SQL Server substitute."""
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import json
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy import select
from app.main import app
from app.config import Settings, get_settings
from app.auth import service as svc
from app.auth.crypto import hash_password,verify_password,digest
from app.auth.tables import sessions,limits
from app.student2.tables import TABLES as T
from app.student2.dependencies import get_db
from app.security import get_current_user

PASSWORD='Student-password-2026'
NEW_PASSWORD='Changed-password-2026'
EMAIL='test.student@polytechnic.am'

@pytest.fixture
def auth_api(database,tmp_path,monkeypatch):
    settings=Settings(_env_file=None,local_mail_dir=str(tmp_path/'mailbox'))
    monkeypatch.setattr('app.auth.service.get_settings',lambda:settings)
    monkeypatch.setattr('app.auth.mail.get_settings',lambda:settings)
    monkeypatch.setattr('app.auth.router.get_settings',lambda:settings)
    monkeypatch.setattr(svc,'get_engine',lambda:database)
    def connection():
        with database.begin() as db:yield db
    app.dependency_overrides.clear()
    app.dependency_overrides[get_db]=connection
    with database.begin() as db:
        db.execute(T['Institutes'].insert().values(InstituteID=1,Name='Institute',ShortName='I',IsActive=True))
        db.execute(T['Chairs'].insert().values(ChairID=1,InstituteID=1,Name='Chair',ShortName='C',IsActive=True))
        db.execute(T['Specializations'].insert().values(SpecializationID=1,ChairID=1,Name='Spec',Code='S',IsActive=True))
        db.execute(T['StudentGroups'].insert().values(GroupID=1,SpecializationID=1,GroupCode='Test-1',EnrollmentYear=2026,IsActive=True))
        db.execute(T['Admins'].update().where(T['Admins'].c.AdminID==1).values(Email='admin@example.test',PasswordHash=hash_password(PASSWORD),IsEmailVerified=True))
    with TestClient(app) as client:
        client.headers['X-ProfRates-Request']='1'
        yield client,database,settings
    app.dependency_overrides.clear()

def post(client,path,body=None,**kwargs):
    headers=kwargs.pop('headers',{})
    csrf=client.cookies.get('pr_csrf')
    if csrf:headers['X-CSRF-Token']=csrf
    return client.post(path,json=body or {},headers=headers,**kwargs)

def registration(**patch):
    return {'Email':EMAIL,'Password':PASSWORD,**patch}

def messages(settings):
    folder=Path(settings.local_mail_dir)
    return sorted([json.loads(p.read_text(encoding='utf-8')) for p in folder.glob('*.json')],key=lambda r:r['purpose'])

def token(settings,purpose='verify',email=EMAIL):
    items=[m for m in messages(settings) if m['purpose']==purpose and m['recipient']==email]
    return parse_qs(urlsplit(items[-1]['link']).fragment)['token'][0]

def provision(client,**patch):
    assert sign_in(client,'admin@example.test',admin=True).status_code==200
    result=post(client,'/api/admin/users',{'FirstName':'Anna','LastName':'Test','GroupID':1,**registration(),**patch})
    assert post(client,'/api/auth/logout').status_code==200
    return result


def verified(client,settings):
    assert provision(client).status_code==201
    return 'x'*43


def sign_in(client,email=EMAIL,password=PASSWORD,admin=False):
    return post(client,'/api/auth/admin/login' if admin else '/api/auth/login',{'Email':email,'Password':password})

def test_password_hash_is_salted_and_verified():
    a=hash_password(PASSWORD);b=hash_password(PASSWORD)
    assert a!=b and PASSWORD not in a
    assert verify_password(PASSWORD,a)
    assert not verify_password('wrong',a)
    for bad in ['demo_HASH','plain',None,'pbkdf2_sha256$1$bad$bad']:
        assert not verify_password(PASSWORD,bad)

def test_registration_verification_login_logout(auth_api):
    c,db,s=auth_api
    code=verified(c,s)
    assert post(c,'/api/auth/verify-email',{'Token':code}).status_code==400
    assert sign_in(c).status_code==200
    assert c.get('/api/auth/session').json()['role']=='student'
    cookie=c.cookies.get('pr_session')
    assert c.get('/api/me/ratings').status_code==200
    assert post(c,'/api/auth/logout').status_code==200
    assert c.get('/api/auth/session').status_code==401
    c.cookies.set('pr_session',cookie)
    assert c.get('/api/auth/session').status_code==401
    with db.begin() as conn:
        row=conn.execute(select(T['Users']).where(T['Users'].c.Email==EMAIL)).mappings().one()
        assert verify_password(PASSWORD,row['PasswordHash']) and row['IsEmailVerified']
        assert conn.execute(select(sessions)).first() is None






def test_recovery_non_enumerating_hash_only_and_local_mail(auth_api):
    c,db,s=auth_api
    verified(c,s)
    known=post(c,'/api/auth/forgot-password',{'Email':EMAIL})
    unknown=post(c,'/api/auth/forgot-password',{'Email':'unknown@polytechnic.am'})
    assert known.status_code==unknown.status_code==200 and known.json()==unknown.json()
    code=token(s,'reset')
    assert code not in known.text
    assert messages(s)[-1]['delivery']=='local-test-only'
    with db.begin() as conn:
        row=conn.execute(select(T['PasswordResets']).where(T['PasswordResets'].c.Code==digest(code))).mappings().one()
        assert row['Purpose']=='reset' and len(row['Code'])==64
        assert code not in str(conn.execute(select(T['ActivityLogs'])).all())
    assert c.get('/api/auth/local-mailbox').status_code==404
    assert c.get('/frontend/var/mailbox').status_code==404

def test_reset_changes_password_invalidates_session_and_replay(auth_api):
    c,db,s=auth_api
    verified(c,s)
    assert sign_in(c).status_code==200
    old_cookie=c.cookies.get('pr_session')
    assert post(c,'/api/auth/forgot-password',{'Email':EMAIL}).status_code==200
    code=token(s,'reset')
    assert post(c,'/api/auth/reset-password',{'Token':code,'Password':NEW_PASSWORD}).status_code==200
    assert c.get('/api/auth/session').status_code==401
    assert post(c,'/api/auth/reset-password',{'Token':code,'Password':NEW_PASSWORD}).status_code==400
    c.cookies.clear()
    assert sign_in(c).status_code==401
    assert sign_in(c,password=NEW_PASSWORD).status_code==200
    with db.begin() as conn:
        assert not conn.execute(select(sessions).where(sessions.c.SessionHash==digest(old_cookie))).first()

@pytest.mark.parametrize('purpose',['reset','verify'])
def test_invalid_expired_and_wrong_purpose_tokens(auth_api,purpose):
    c,db,s=auth_api
    verified(c,s)
    post(c,'/api/auth/forgot-password',{'Email':EMAIL})
    code=token(s,'reset')
    endpoint='/api/auth/'+('reset-password' if purpose=='reset' else 'verify-email')
    payload={'Token':code,**({'Password':NEW_PASSWORD} if purpose=='reset' else {})}
    if purpose=='verify':
        assert post(c,endpoint,payload).status_code==400
    with db.begin() as conn:
        conn.execute(T['PasswordResets'].update().values(Expiry=svc.now()-timedelta(minutes=1)))
    assert post(c,endpoint,payload).status_code==400
    assert post(c,endpoint,{**payload,'Token':'x'*43}).status_code==400

def test_csrf_and_cross_origin_rejected(auth_api):
    c,_,s=auth_api
    verified(c,s);sign_in(c)
    assert c.post('/api/auth/logout',json={}).status_code==403
    assert post(c,'/api/auth/logout',headers={'Origin':'https://attacker.test'}).status_code==403
    assert post(c,'/api/auth/logout',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert post(c,'/api/auth/logout').status_code==200

def test_anonymous_and_forged_identity_rejected(auth_api):
    c,_,_=auth_api
    for path in ['/api/me/ratings','/api/admin/users','/api/admin/activity-logs','/api/admin/dashboard','/api/admin/password-resets']:
        assert c.get(path,headers={'X-Role':'admin','X-User-ID':'1','Authorization':'Bearer fake'}).status_code==401
    assert c.post('/api/auth/login',json={'Email':EMAIL,'Password':PASSWORD},headers={'X-ProfRates-Request':'0'}).status_code==403

def test_admin_dashboard_users_logs_and_student_denial(auth_api):
    c,db,s=auth_api
    verified(c,s);sign_in(c)
    for path in ['/api/admin/users','/api/admin/dashboard','/api/admin/activity-logs','/api/admin/password-resets']:
        assert c.get(path).status_code==403
    post(c,'/api/auth/logout')
    assert sign_in(c,'admin@example.test',admin=True).status_code==200
    assert c.get('/api/auth/session').json()['role']=='admin'
    for path in ['/api/admin/users','/api/admin/dashboard','/api/admin/activity-logs','/api/admin/password-resets']:
        result=c.get(path);assert result.status_code==200
        assert 'PasswordHash' not in result.text and '"Code"' not in result.text and '"CSRFHash"' not in result.text
    assert c.get('/api/me/ratings').status_code==403
    data=c.get('/api/admin/dashboard').json()
    assert data['users']==2 and data['admin']['Email']=='admin@example.test'
    users=c.get('/api/admin/users?q=Anna').json()['items'];assert len(users)==1
    item=users[0]
    headers={'X-CSRF-Token':c.cookies.get('pr_csrf')}
    changed=c.put('/api/admin/users/'+str(item['UserID']),json={k:item[k] for k in ['FirstName','LastName','GroupID']}|{'Status':'Suspended'},headers=headers)
    assert changed.status_code==200 and changed.json()['Status']=='Suspended'
    assert c.put('/api/admin/users/'+str(item['UserID']),json={'Role':'admin'},headers=headers).status_code==422
    assert c.put('/api/admin/users/999',json={k:item[k] for k in ['FirstName','LastName','GroupID']}|{'Status':'Active'},headers=headers).status_code==404
    post(c,'/api/auth/logout')
    assert sign_in(c).status_code==401

def test_student_cannot_access_another_users_ratings(auth_api):
    c,_,s=auth_api
    verified(c,s);sign_in(c)
    assert c.get('/api/me/ratings?user_id=1').json()['total']==0
    assert c.get('/api/me/ratings/999').status_code==404

def test_admin_password_recovery_and_unverified_admin(auth_api):
    c,db,s=auth_api
    assert post(c,'/api/auth/admin/forgot-password',{'Email':'admin@example.test'}).status_code==200
    code=token(s,'reset','admin@example.test')
    assert post(c,'/api/auth/reset-password',{'Token':code,'Password':NEW_PASSWORD}).status_code==400
    assert post(c,'/api/auth/admin/reset-password',{'Token':code,'Password':NEW_PASSWORD}).status_code==200
    assert sign_in(c,'admin@example.test',NEW_PASSWORD,True).status_code==200
    post(c,'/api/auth/logout')
    with db.begin() as conn:
        conn.execute(T['Admins'].update().values(IsEmailVerified=False))
    count=len(messages(s))
    post(c,'/api/auth/admin/forgot-password',{'Email':'admin@example.test'})
    assert len(messages(s))==count

def test_recovery_routes_bind_role_and_do_not_consume_mismatched_tokens(auth_api):
    c,db,s=auth_api
    verified(c,s)
    assert post(c,'/api/auth/forgot-password',{'Email':'admin@example.test','Role':'admin'}).status_code==422
    assert post(c,'/api/auth/student/forgot-password',{'Email':'admin@example.test'}).status_code==200
    assert not [m for m in messages(s) if m['recipient']=='admin@example.test']
    assert post(c,'/api/auth/admin/forgot-password',{'Email':EMAIL}).status_code==200
    assert not [m for m in messages(s) if m['recipient']==EMAIL and m['purpose']=='reset']

    assert post(c,'/api/auth/student/forgot-password',{'Email':EMAIL}).status_code==200
    student_token=token(s,'reset',EMAIL)
    assert post(c,'/api/auth/admin/reset-password',{'Token':student_token,'Password':NEW_PASSWORD}).status_code==400
    with db.begin() as conn:
        student_row=conn.execute(select(T['PasswordResets']).where(T['PasswordResets'].c.Code==digest(student_token))).mappings().one()
        assert not student_row['IsUsed']
    assert post(c,'/api/auth/student/reset-password',{'Token':student_token,'Password':NEW_PASSWORD}).status_code==200

    assert post(c,'/api/auth/admin/forgot-password',{'Email':'admin@example.test'}).status_code==200
    admin_token=token(s,'reset','admin@example.test')
    assert post(c,'/api/auth/student/reset-password',{'Token':admin_token,'Password':NEW_PASSWORD}).status_code==400
    assert post(c,'/api/auth/admin/reset-password',{'Token':admin_token,'Password':NEW_PASSWORD}).status_code==200

def test_rate_limit_persists_in_database(auth_api):
    c,db,s=auth_api
    for i in range(4):assert post(c,'/api/auth/forgot-password',{'Email':EMAIL}).status_code==200
    assert post(c,'/api/auth/forgot-password',{'Email':EMAIL}).status_code==429
    with db.begin() as conn:assert conn.execute(select(limits)).first()

def test_validation_errors_never_echo_password(auth_api):
    c,_,_=auth_api
    password='private-invalid-password'*20
    result=post(c,'/api/auth/login',{**registration(),'Password':password})
    assert result.status_code==422 and password not in result.text

@pytest.mark.parametrize('patch',[
    {'app_env':'production'},
    {'app_env':'production','public_base_url':'https://example.test','cookie_secure':True,'mail_backend':'local'},
    {'local_mail_dir':str(Path(__file__).resolve().parents[1]/'frontend'/'mail')},
])
def test_unsafe_production_configuration_fails(patch):
    with pytest.raises(ValidationError):Settings(_env_file=None,**patch)

def test_production_disabled_mail_never_exposes_token(auth_api,monkeypatch):
    from app.auth.mail import get_mailer,MailDeliveryError
    s=Settings(_env_file=None,app_env='production',public_base_url='https://example.test',cookie_secure=True,mail_backend='disabled')
    monkeypatch.setattr('app.auth.mail.get_settings',lambda:s)
    with pytest.raises(MailDeliveryError):get_mailer()
    c,_,_=auth_api
    assert c.get('/api/auth/local-mailbox').status_code==404
    assert c.get('/api/auth/forgot-password').status_code==405

def test_session_cookie_flags_and_expiry(auth_api):
    c,db,s=auth_api
    verified(c,s);r=sign_in(c)
    cookies=' '.join(r.headers.get_list('set-cookie')).lower()
    assert 'httponly' in cookies and 'samesite=strict' in cookies
    with db.begin() as conn:conn.execute(sessions.update().values(ExpiresAt=svc.now()-timedelta(seconds=1)))
    assert c.get('/api/auth/session').status_code==401

def test_auth_database_failure_does_not_leak(auth_api,monkeypatch):
    from sqlalchemy.exc import OperationalError
    c,_,s=auth_api
    verified(c,s);sign_in(c)
    def broken():raise OperationalError('server=internal',{},Exception('password=secret'))
    monkeypatch.setattr(svc,'get_engine',broken)
    result=c.get('/api/auth/session')
    assert result.status_code==503 and 'internal' not in result.text and 'secret' not in result.text


def test_smtp_delivery_component_uses_tls_without_exposing_link(auth_api,monkeypatch):
    from app.auth.mail import SMTPMailer
    c,db,s=auth_api
    s.mail_backend='smtp';s.smtp_host='smtp.example.test';s.smtp_from='sender@example.test'
    calls=[]
    class FakeSMTP:
        def __init__(self,host,port,timeout):calls.append(('connect',host,port))
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def starttls(self,context):calls.append(('tls',True))
        def send_message(self,message):calls.append(('accepted',message['To']))
    monkeypatch.setattr('app.auth.mail.smtplib.SMTP',FakeSMTP)
    SMTPMailer().send(EMAIL,'reset','https://example.test/#private-token')
    assert calls==[('connect','smtp.example.test',587),('tls',True),('accepted',EMAIL)]

def test_mail_failure_is_audited_without_claiming_sent(auth_api,monkeypatch):
    from app.auth.mail import MailDeliveryError
    c,db,s=auth_api
    verified(c,s)
    class Failing:
        def send(self,*args):raise MailDeliveryError('private internal configuration')
    monkeypatch.setattr(svc,'get_mailer',lambda:Failing())
    result=post(c,'/api/auth/forgot-password',{'Email':EMAIL})
    assert result.status_code==200 and 'private internal' not in result.text
    with db.begin() as conn:
        assert conn.execute(select(T['ActivityLogs']).where(T['ActivityLogs'].c.ActionType=='MailDelivery',T['ActivityLogs'].c.Status=='Failed')).first()

def test_expired_verification_and_resend(auth_api):
    c,db,s=auth_api
    verified(c,s)
    with db.begin() as conn:
        conn.execute(T['Users'].update().where(T['Users'].c.Email==EMAIL).values(IsEmailVerified=False))
        user=conn.execute(select(T['Users']).where(T['Users'].c.Email==EMAIL)).mappings().one()
        svc.issue_link(conn,user,'student','verify')
    old=token(s)
    with db.begin() as conn:
        conn.execute(T['PasswordResets'].update().values(Expiry=svc.now()-timedelta(minutes=1)))
    assert post(c,'/api/auth/verify-email',{'Token':old}).status_code==400
    assert post(c,'/api/auth/resend-verification',{'Email':EMAIL}).status_code==200
    fresh=token(s)
    # Locate the newest filesystem message; do not depend on random filenames.
    files=sorted(Path(s.local_mail_dir).glob('*.json'),key=lambda p:p.stat().st_mtime)
    newest=json.loads(files[-1].read_text(encoding='utf-8'))
    fresh=parse_qs(urlsplit(newest['link']).fragment)['token'][0]
    assert post(c,'/api/auth/verify-email',{'Token':fresh}).status_code==200
    assert post(c,'/api/auth/verify-email',{'Token':old}).status_code==400
    count=len(messages(s))
    assert post(c,'/api/auth/resend-verification',{'Email':EMAIL}).status_code==200
    assert len(messages(s))==count


def test_administrator_html_is_protected(auth_api):
    c,db,s=auth_api
    response=c.get('/frontend/admin_portal/users.html')
    assert response.status_code==200 and 'Admin_login_eng.html' in str(response.url)
    verified(c,s);sign_in(c)
    assert c.get('/frontend/admin_portal/users.html').status_code==403
    post(c,'/api/auth/logout')
    sign_in(c,'admin@example.test',admin=True)
    response=c.get('/frontend/admin_portal/users.html')
    assert response.status_code==200 and 'js_folder/accounts.js' in response.text

def test_frontend_recovery_and_admin_wiring(auth_api):
    from bs4 import BeautifulSoup
    c,_,_=auth_api
    root=Path(__file__).resolve().parents[1]/'frontend'
    recovery=BeautifulSoup((root/'account_recovery.html').read_text(encoding='utf-8'),'html.parser')
    assert recovery.select_one('script[src^="js_codes/account_recovery.js"]')
    for filename in ('account_recovery.html','account_recovery_en.html',
                     'admin_portal/account_recovery_arm.html','admin_portal/account_recovery_eng.html'):
        response=c.get('/frontend/'+filename)
        assert response.status_code==200
        assert response.headers.get('Cache-Control')=='no-store'
    for name in ['users.html','users_arm.html','dashboard.html','ActivityLogs_arm.html','ResetPassword.html','Admin_login_eng.html']:
        soup=BeautifulSoup((root/'admin_portal'/name).read_text(encoding='utf-8'),'html.parser')
        sources=[node.get('src').split('?')[0] for node in soup.select('script[src]')]
        assert sources.index('../js_codes/api.js')<sources.index('js_folder/accounts.js')
        assert 'js_folder/admin.js' not in sources and 'js_folder/reset_eng.js' not in sources


def test_student_remember_me_controls_cookie_and_server_expiry(auth_api):
    c,db,s=auth_api
    verified(c,s)
    normal=post(c,'/api/auth/login',{'Email':EMAIL,'Password':PASSWORD,'RememberMe':False})
    assert normal.status_code==200
    assert all('max-age' not in h.lower()for h in normal.headers.get_list('set-cookie'))
    with db.connect() as conn:
        row=conn.execute(select(sessions).where(sessions.c.SessionHash==digest(c.cookies.get('pr_session')))).mappings().one()
        assert abs((row['ExpiresAt']-row['CreatedAt']).total_seconds()-s.session_hours*3600)<2
    post(c,'/api/auth/logout')
    persistent=post(c,'/api/auth/login',{'Email':EMAIL,'Password':PASSWORD,'RememberMe':True})
    assert persistent.status_code==200
    assert all(f'max-age={s.remember_session_days*86400}'in h.lower()for h in persistent.headers.get_list('set-cookie'))
    with db.connect() as conn:
        row=conn.execute(select(sessions).where(sessions.c.SessionHash==digest(c.cookies.get('pr_session')))).mappings().one()
        assert abs((row['ExpiresAt']-row['CreatedAt']).total_seconds()-s.remember_session_days*86400)<2
    assert post(c,'/api/auth/logout').status_code==200
    assert c.get('/api/auth/session').status_code==401


def test_remember_me_is_strict_and_not_admin_registration_input(auth_api):
    c,_,_=auth_api
    assert post(c,'/api/auth/login',{'Email':EMAIL,'Password':PASSWORD,'RememberMe':'false'}).status_code==422
    assert post(c,'/api/auth/admin/login',{'Email':'admin@example.test','Password':PASSWORD,'RememberMe':True}).status_code==422









def test_public_registration_and_roster_removed(auth_api):
    c,_,_=auth_api
    assert post(c,'/api/auth/register',registration()).status_code==404
    for page in ['sign_up_arm.html','sign_up_eng.html']:
        assert c.get('/frontend/'+page).status_code==404
    assert sign_in(c,'admin@example.test',admin=True).status_code==200
    assert c.get('/api/admin/student-roster').status_code==404


def test_admin_provisions_ready_account_without_roster(auth_api):
    c,engine,s=auth_api
    response=provision(c)
    assert response.status_code==201,response.text
    assert response.json()['academic_status']=='term-unconfigured'
    assert PASSWORD not in response.text and 'PasswordHash' not in response.text
    assert messages(s)==[]
    with engine.connect() as db:
        user=db.execute(select(T['Users']).where(T['Users'].c.Email==EMAIL)).mappings().one()
        assert user['GroupID']==1 and user['IsEmailVerified']
        assert verify_password(PASSWORD,user['PasswordHash'])
        assert 'StudentRoster' not in T
    assert sign_in(c).status_code==200
    assert post(c,'/api/admin/users',{'FirstName':'X','LastName':'Y','GroupID':1,**registration(Email='other@polytechnic.am')}).status_code==403
    post(c,'/api/auth/logout')
    assert post(c,'/api/admin/users',{'FirstName':'X','LastName':'Y','GroupID':1,**registration()}).status_code==401


def test_duplicate_student_and_invalid_credentials(auth_api):
    c,_,_=auth_api
    assert provision(c).status_code==201
    assert provision(c,Email=EMAIL.upper()).status_code==409
    assert sign_in(c,password='wrong').status_code==401
    assert sign_in(c,email='unknown@polytechnic.am').status_code==401


@pytest.mark.parametrize('patch',[{'FirstName':' '},{'LastName':''},{'GroupID':999},{'GroupID':True},
    {'Email':'x@gmail.com'},{'Password':'short'},{'Role':'admin'},{'IsEmailVerified':True}])
def test_admin_create_validation(auth_api,patch):
    c,_,_=auth_api
    assert provision(c,**patch).status_code==422


def test_admin_create_and_audit_are_one_transaction(auth_api,monkeypatch):
    from fastapi import HTTPException
    c,engine,_=auth_api
    sign_in(c,'admin@example.test',admin=True)
    original=svc.audit
    def fail(db,actor,action,*args,**kwargs):
        if action=='StudentCreated':raise HTTPException(503,'Audit unavailable')
        return original(db,actor,action,*args,**kwargs)
    monkeypatch.setattr(svc,'audit',fail)
    response=post(c,'/api/admin/users',{'FirstName':'Anna','LastName':'Test','GroupID':1,**registration()})
    assert response.status_code==503
    with engine.connect() as db:
        assert db.execute(select(T['Users'].c.UserID).where(T['Users'].c.Email==EMAIL)).first() is None

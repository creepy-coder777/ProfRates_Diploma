"""Trusted local operator CLI. Requires SQL credentials/Windows DB access.
Never exposes a public administrator registration or password-changing endpoint.
"""
import argparse
import getpass
from sqlalchemy import select,func
from app.database import get_engine
from app.student2.tables import TABLES as T
from app.auth.crypto import hash_password
from app.auth import service as svc
from app.auth.schemas import EmailInput,RecoveryInput
from app.security import Principal

def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['create','recover','verify-email'])
    parser.add_argument('--email',required=True)
    parser.add_argument('--first-name',default='Administrator')
    parser.add_argument('--last-name',default='')
    parser.add_argument('--trusted-email',action='store_true',help='Operator explicitly attests ownership of this email for recovery')
    args=parser.parse_args(argv)
    email=EmailInput(Email=args.email).Email
    password=None
    if args.action in {'create','recover'}:
        password=getpass.getpass('New password (12-128 characters): ')
        if not 12<=len(password)<=128 or password!=getpass.getpass('Confirm password: '):
            print('Password length or confirmation invalid. Nothing changed.')
            return 1
    try:
        with get_engine().connect().execution_options(isolation_level='SERIALIZABLE') as db:
            with db.begin():
                a=T['Admins']
                row=db.execute(select(a).where(func.lower(a.c.Email)==email)).mappings().first()
                if args.action=='create':
                    if row:
                        print('Administrator already exists. Use recover.');return 1
                    ident=db.execute(a.insert().values(Email=email,FirstName=args.first_name,LastName=args.last_name or None,
                        PasswordHash=hash_password(password),IsEmailVerified=args.trusted_email)).inserted_primary_key[0]
                    svc.audit(db,Principal(None,True,ident),'AdminCreated',f'Admins:{ident}')
                elif not row:
                    print('Administrator not found. Nothing changed.');return 1
                elif args.action=='recover':
                    ident=row['AdminID']
                    db.execute(a.update().where(a.c.AdminID==ident).values(PasswordHash=hash_password(password)))
                    db.execute(svc.sessions.delete().where(svc.sessions.c.AdminID==ident))
                    db.execute(T['PasswordResets'].update().where(T['PasswordResets'].c.AdminID==ident).values(IsUsed=True))
                    svc.audit(db,Principal(None,True,ident),'AdminOfflineRecovery',f'Admins:{ident}')
                else:
                    svc.issue_link(db,row,'admin','verify')
        print('Operation completed. For verify-email, inspect configured delivery and audit status.')
        return 0
    except Exception:
        print('Operation failed; no password or connection details displayed. Check DB access and migration.')
        return 1

if __name__=='__main__':
    raise SystemExit(main())

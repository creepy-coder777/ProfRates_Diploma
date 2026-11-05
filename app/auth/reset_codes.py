"""Six-digit reset codes; successful verification grants a short-lived reset token."""
import hashlib
import hmac
import secrets
from datetime import timedelta
from sqlalchemy import select, func
from app.auth import service as svc
from app.auth.mail import get_mailer, MailDeliveryError
from app.auth.crypto import new_token, digest
from app.student2.tables import TABLES as T


def encode_code(code, salt=None):
    salt = salt or secrets.token_bytes(8)
    hashed = hashlib.pbkdf2_hmac('sha256', code.encode('ascii'), salt, 600_000, dklen=22)
    return 'otp$' + salt.hex() + hashed.hex()


DUMMY_CODE = encode_code('000000')


def matches(code, encoded):
    if not encoded or len(encoded) != 64 or not encoded.startswith('otp$'):
        encoded = DUMMY_CODE
        valid = False
    else:
        valid = True
    try:
        actual = encode_code(code, bytes.fromhex(encoded[4:20]))
        return hmac.compare_digest(actual, encoded) and valid
    except (ValueError, UnicodeEncodeError):
        return False


def request_code(db, payload, role):
    table, key = svc.account_table(role)
    user = db.execute(select(table).where(
        func.lower(table.c.Email) == payload.Email
    )).mappings().first()
    eligible = user and user['IsEmailVerified'] and (role == 'admin' or user['Status'] == 'Active')
    svc.audit(db, None, 'RecoveryCodeRequest', f'{role}:{user[key]}' if user else role)
    if not eligible:
        return
    resets = T['PasswordResets']
    owner = resets.c.AdminID if role == 'admin' else resets.c.UserID
    db.execute(resets.update().where(owner == user[key], resets.c.Purpose == 'reset',
                                    resets.c.IsUsed == False).values(IsUsed=True))
    code = f'{secrets.randbelow(1_000_000):06d}'
    encoded = encode_code(code)
    db.execute(resets.insert().values(UserID=user[key] if role == 'student' else None,
        AdminID=user[key] if role == 'admin' else None, Code=encoded, Purpose='reset',
        Expiry=svc.now()+timedelta(minutes=10), IsUsed=False, CreatedAt=svc.now()))
    try:
        get_mailer().send(user['Email'], 'reset-code', code)
    except MailDeliveryError:
        db.execute(resets.update().where(owner == user[key], resets.c.Code == encoded).values(IsUsed=True))
        svc.audit(db, None, 'MailDelivery', f'{role}:{user[key]}:reset-code', 'Failed')
        return
    svc.audit(db, None, 'MailDelivery', f'{role}:{user[key]}:reset-code',
              'LocalTest' if svc.get_settings().mail_backend == 'local' else 'Sent')


def verify_code(db, payload, role):
    table, key = svc.account_table(role)
    user = db.execute(select(table).where(func.lower(table.c.Email) == payload.Email)).mappings().first()
    resets = T['PasswordResets']
    owner = resets.c.AdminID if role == 'admin' else resets.c.UserID
    row = None
    eligible = user and user['IsEmailVerified'] and (role == 'admin' or user['Status'] == 'Active')
    if eligible:
        row = db.execute(select(resets).where(owner == user[key], resets.c.Purpose == 'reset',
            resets.c.IsUsed == False, resets.c.Expiry > svc.now(),
            resets.c.Code.startswith('otp$')).order_by(resets.c.ResetID.desc())).mappings().first()
    valid = matches(payload.Code, row['Code'] if row else None)
    if not valid or row is None:
        svc.audit(db, None, 'RecoveryCodeVerify', role, 'Failed')
        return None
    token = new_token()
    changed = db.execute(resets.update().where(resets.c.ResetID == row['ResetID'],
        resets.c.Code == row['Code'], resets.c.IsUsed == False,
        resets.c.Expiry > svc.now()).values(Code=digest(token), Expiry=svc.now()+timedelta(minutes=5)))
    if changed.rowcount != 1:
        return None
    svc.audit(db, None, 'RecoveryCodeVerify', f'{role}:{user[key]}')
    return token

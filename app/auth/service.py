from datetime import datetime, timedelta, timezone
import time
from urllib.parse import urlencode
from sqlalchemy import select, func, or_
from fastapi import HTTPException
from app.config import get_settings
from app.database import get_engine
from app.security import Principal
from app.student2.tables import TABLES as T
from app.auth.tables import sessions, limits
from app.auth.crypto import digest, new_token, hash_password, verify_password, DUMMY_HASH
from app.auth.mail import get_mailer, MailDeliveryError


def now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def audit(db, actor, action, target=None, status="Success"):
    db.execute(
        T["ActivityLogs"]
        .insert()
        .values(
            UserID=actor.user_id if actor else None,
            AdminID=actor.admin_id if actor else None,
            ActionType=action,
            Target=target,
            Status=status,
            CreatedAt=now(),
        )
    )


def account_table(role):
    return (T["Admins"], "AdminID") if role == "admin" else (T["Users"], "UserID")


def principal(row, role):
    return (
        Principal(None, True, row["AdminID"])
        if role == "admin"
        else Principal(row["UserID"], False)
    )


def throttle(db, request, action, email="", maximum=8, seconds=900):
    # Database serialization protects counters across workers. No raw email/IP stored.
    ip = request.client.host if request.client else "unknown"
    start = int(time.time()) // seconds * seconds
    allowed = True
    for suffix, limit in [(ip, maximum * 4), (email, maximum)]:
        if not suffix:
            continue
        key = digest(action + ":" + suffix)
        row = db.execute(select(limits).where(limits.c.KeyHash == key)).mappings().first()
        attempts = row["Attempts"] + 1 if row and row["WindowStart"] == start else 1
        if row:
            db.execute(
                limits.update()
                .where(limits.c.KeyHash == key)
                .values(WindowStart=start, Attempts=attempts)
            )
        else:
            db.execute(limits.insert().values(KeyHash=key, WindowStart=start, Attempts=attempts))
        allowed = allowed and attempts <= limit
    db.execute(limits.delete().where(limits.c.WindowStart < int(time.time()) - 86400))
    return allowed


def issue_link(db, row, role, purpose, language="hy"):
    t = T["PasswordResets"]
    col = t.c.AdminID if role == "admin" else t.c.UserID
    ident = row["AdminID" if role == "admin" else "UserID"]
    # One active link per account/purpose. Different purposes remain independent.
    db.execute(
        t.update()
        .where(col == ident, t.c.Purpose == purpose, t.c.IsUsed == False)
        .values(IsUsed=True)
    )
    token = new_token()
    db.execute(
        t.insert().values(
            UserID=None if role == "admin" else ident,
            AdminID=ident if role == "admin" else None,
            Code=digest(token),
            Purpose=purpose,
            Expiry=now()
            + timedelta(
                minutes=get_settings().verification_minutes
                if purpose == "verify"
                else get_settings().reset_minutes
            ),
            IsUsed=False,
            CreatedAt=now(),
        )
    )
    # Fragment never reaches web server access logs. Frontend clears it immediately.
    page = "account_recovery.html" if language == "hy" else "account_recovery_en.html"
    if role == "admin":
        page = (
            "admin_portal/account_recovery_arm.html"
            if language == "hy"
            else "admin_portal/account_recovery_eng.html"
        )
    link = (
        get_settings().public_base_url.rstrip("/")
        + "/frontend/"
        + page
        + "#"
        + urlencode({"token": token, "purpose": purpose})
    )
    try:
        get_mailer().send(row["Email"], purpose, link)
    except MailDeliveryError:
        # Do not expose account existence or delivery differences to anonymous clients.
        audit(db, None, "MailDelivery", f"{role}:{ident}:{purpose}", "Failed")
        return False
    audit(
        db,
        None,
        "MailDelivery",
        f"{role}:{ident}:{purpose}",
        "LocalTest" if get_settings().mail_backend == "local" else "Sent",
    )
    return True


def session_lifetime(payload, role):
    settings = get_settings()
    if role == "student" and getattr(payload, "RememberMe", False):
        return timedelta(days=settings.remember_session_days)
    return timedelta(hours=settings.session_hours)


def login(db, payload, role):
    table, key = account_table(role)
    row = (
        db.execute(select(table).where(func.lower(table.c.Email) == payload.Email))
        .mappings()
        .first()
    )
    valid = verify_password(payload.Password, row["PasswordHash"] if row else DUMMY_HASH)
    actor = principal(row, role) if row else None
    if not valid or (
        role == "student" and (row["Status"] != "Active" or not row["IsEmailVerified"])
    ):
        audit(db, None, "Login", f"{table.name}:{row[key]}" if row else role, "Failed")
        return None
    if role == 'student':
        from app.auth.academic import sync_student
        academic_status = sync_student(db, actor.user_id)
        audit(db, actor, 'AcademicSync', f'Users:{actor.user_id}:{academic_status}')
    db.execute(table.update().where(table.c[key] == row[key]).values(LastLogin=now()))
    token, csrf = new_token(), new_token()
    expiry = now() + session_lifetime(payload, role)
    db.execute(
        sessions.insert().values(
            SessionHash=digest(token),
            CSRFHash=digest(csrf),
            UserID=actor.user_id,
            AdminID=actor.admin_id,
            CreatedAt=now(),
            ExpiresAt=expiry,
        )
    )
    db.execute(sessions.delete().where(sessions.c.ExpiresAt <= now()))
    audit(db, actor, "Login", role)
    return token, csrf, actor


def resolve(db, request):
    token = request.cookies.get("pr_session", "")
    if not 40 <= len(token) <= 100:
        raise HTTPException(401, "Sign in required.")
    row = (
        db.execute(
            select(sessions).where(
                sessions.c.SessionHash == digest(token), sessions.c.ExpiresAt > now()
            )
        )
        .mappings()
        .first()
    )
    if not row:
        raise HTTPException(401, "Session expired. Sign in again.")
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        if digest(request.headers.get("x-csrf-token", "")) != row["CSRFHash"]:
            raise HTTPException(403, "Invalid CSRF token.")
    if row["AdminID"] is not None:
        table, key = T["Admins"], "AdminID"
        user = db.execute(select(table.c.AdminID).where(table.c.AdminID == row["AdminID"])).first()
        actor = Principal(None, True, row["AdminID"])
    else:
        table = T["Users"]
        user = db.execute(
            select(table.c.UserID).where(
                table.c.UserID == row["UserID"],
                table.c.Status == "Active",
                table.c.IsEmailVerified == True,
            )
        ).first()
        actor = Principal(row["UserID"], False)
    if not user:
        raise HTTPException(401, "Account is not available.")
    return actor


def resolve_principal(request):
    if not request.cookies.get("pr_session"):
        raise HTTPException(401, "Sign in required.")
    from app.database import DatabaseNotConfigured
    from sqlalchemy.exc import SQLAlchemyError

    try:
        with get_engine().connect() as db:
            return resolve(db, request)
    except (SQLAlchemyError, DatabaseNotConfigured, ImportError):
        raise HTTPException(503, "Authentication database unavailable.") from None


def recovery(db, payload, purpose="reset", role=None):
    role = role or getattr(payload, "Role", "student")
    table, key = account_table(role)
    row = (
        db.execute(select(table).where(func.lower(table.c.Email) == payload.Email))
        .mappings()
        .first()
    )
    audit(
        db,
        None,
        "RecoveryRequest" if purpose == "reset" else "VerificationRequest",
        f"{table.name}:{row[key]}" if row else role,
    )
    if not row:
        return
    if purpose == "verify":
        eligible = role == "student" and row["Status"] == "Active" and not row["IsEmailVerified"]
    else:
        eligible = row["IsEmailVerified"] and (role == "admin" or row["Status"] == "Active")
    if eligible:
        issue_link(db, row, role, purpose, getattr(payload, "Language", "hy"))


def consume(db, token, purpose, password=None, expected_role=None):
    t = T["PasswordResets"]
    row = (
        db.execute(
            select(t).where(
                t.c.Code == digest(token),
                t.c.Purpose == purpose,
                t.c.IsUsed == False,
                t.c.Expiry > now(),
            )
        )
        .mappings()
        .first()
    )
    if not row:
        return False
    role = "admin" if row["AdminID"] is not None else "student"
    if expected_role is not None and role != expected_role:
        return False
    # Conditional write + serializable transaction: only one request can consume.
    changed = db.execute(
        t.update()
        .where(t.c.ResetID == row["ResetID"], t.c.IsUsed == False, t.c.Expiry > now())
        .values(IsUsed=True)
    )
    if changed.rowcount != 1:
        return False
    table, key = account_table(role)
    ident = row[key]
    user = db.execute(select(table).where(table.c[key] == ident)).mappings().first()
    if not user or (role == "student" and user["Status"] != "Active"):
        return False
    actor = principal(user, role)
    if purpose == "verify":
        db.execute(table.update().where(table.c[key] == ident).values(IsEmailVerified=True))
        audit(db, actor, "EmailVerified", f"{table.name}:{ident}")
    else:
        db.execute(
            table.update().where(table.c[key] == ident).values(PasswordHash=hash_password(password))
        )
        owner = sessions.c.AdminID if role == "admin" else sessions.c.UserID
        db.execute(sessions.delete().where(owner == ident))
        col = t.c.AdminID if role == "admin" else t.c.UserID
        db.execute(t.update().where(col == ident, t.c.Purpose == "reset").values(IsUsed=True))
        audit(db, actor, "PasswordChanged", f"{table.name}:{ident}")
    return True

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select
from app.auth import service as svc
from app.auth.schemas import (
    LoginInput,
    StudentLoginInput,
    AdminLoginInput,
    RegisterInput,
    RecoveryRequestInput,
    ResetInput,
    TokenInput,
)
from app.student2.dependencies import get_db
from app.security import get_current_user
from typing import Literal
from app.auth.schemas import ResetCodeInput
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["Accounts"])


def recovery_response(language="hy"):
    if get_settings().mail_backend == "local":
        message = (
            "Եթե հաշիվը համապատասխանում է, մասնավոր տեղային փոստարկղում կարող է ստեղծված լինել թեստային հաղորդագրություն․ նամակ չի ուղարկվել."
            if language == "hy"
            else "If eligible, a private local test message may have been created; no email was sent."
        )
    else:
        message = (
            "Եթե հաշիվը համապատասխանում է, հրահանգները կուղարկվեն կարգավորված ծառայությամբ."
            if language == "hy"
            else "If the account is eligible, instructions will be sent by the configured service."
        )
    return {"message": message}


def limited():
    return JSONResponse(
        {"detail": "Too many attempts. Try again later."}, 429, headers={"Retry-After": "900"}
    )


@router.post("/register", status_code=201)
def register(payload: RegisterInput, request: Request, db=Depends(get_db, scope="function")):
    if not svc.throttle(db, request, "register", payload.Email, 5):
        return limited()
    if svc.register(db, payload) is None:
        return JSONResponse(
            {"detail": "This email is already registered. Try signing in or requesting recovery."},
            409,
        )
    if get_settings().mail_backend == "local":
        message = (
            "Գրանցումն ընդունվել է։ Նամակ չի ուղարկվել․ թեստային հաղորդագրությունը ստեղծվել է մասնավոր տեղային փոստարկղում."
            if payload.Language == "hy"
            else "Registration received. No email was sent; a test message was created in the private local mailbox."
        )
    else:
        message = (
            "Գրանցումն ընդունվել է։ Ստուգեք էլ․ հասցեն և հաստատեք այն՝ մուտք գործելուց առաջ."
            if payload.Language == "hy"
            else "Registration received. Check your email and verify it before signing in."
        )
    return {"message": message}


def sign_in(payload, request, response, db, role):
    if not svc.throttle(db, request, "login:" + role, payload.Email):
        return limited()
    result = svc.login(db, payload, role)
    if result is None:
        return JSONResponse(
            {"detail": "Invalid credentials, inactive account, or unverified student email."}, 401
        )
    token, csrf, actor = result
    settings = get_settings()
    for name, value, http in [("pr_session", token, True), ("pr_csrf", csrf, False)]:
        response.set_cookie(
            name,
            value,
            httponly=http,
            secure=settings.cookie_secure,
            samesite="strict",
            max_age=(
                int(svc.session_lifetime(payload, role).total_seconds())
                if role == "admin" or getattr(payload, "RememberMe", False)
                else None
            ),
            path="/",
        )
    return {"authenticated": True, "role": role}


@router.post("/login")
def login(
    payload: StudentLoginInput,
    request: Request,
    response: Response,
    db=Depends(get_db, scope="function"),
):
    return sign_in(payload, request, response, db, "student")


@router.post("/admin/login")
def admin_login(
    payload: AdminLoginInput,
    request: Request,
    response: Response,
    db=Depends(get_db, scope="function"),
):
    return sign_in(payload, request, response, db, "admin")


@router.get("/session")
def session(request: Request, actor=Depends(get_current_user)):
    return {"authenticated": True, "role": "admin" if actor.is_admin else "student"}


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    actor=Depends(get_current_user),
    db=Depends(get_db, scope="function"),
):
    db.execute(
        svc.sessions.delete().where(
            svc.sessions.c.SessionHash == svc.digest(request.cookies["pr_session"])
        )
    )
    svc.audit(db, actor, "Logout")
    response.delete_cookie("pr_session", path="/")
    response.delete_cookie("pr_csrf", path="/")
    return {"authenticated": False}


def request_recovery(payload, request, db, role, purpose="reset"):
    if not svc.throttle(db, request, f"recovery:{role}:{purpose}", payload.Email, 4):
        return limited()
    svc.recovery(db, payload, purpose, role)
    return recovery_response(payload.Language)


@router.post("/student/forgot-password")
def student_forgot(
    payload: RecoveryRequestInput, request: Request, db=Depends(get_db, scope="function")
):
    return request_recovery(payload, request, db, "student")


@router.post("/admin/forgot-password")
def admin_forgot(
    payload: RecoveryRequestInput, request: Request, db=Depends(get_db, scope="function")
):
    return request_recovery(payload, request, db, "admin")


@router.post("/forgot-password")
def forgot(payload: RecoveryRequestInput, request: Request, db=Depends(get_db, scope="function")):
    return request_recovery(payload, request, db, "student")


@router.post("/resend-verification")
def resend(payload: RecoveryRequestInput, request: Request, db=Depends(get_db, scope="function")):
    return request_recovery(payload, request, db, "student", "verify")


@router.post("/student/resend-verification")
def student_resend(
    payload: RecoveryRequestInput, request: Request, db=Depends(get_db, scope="function")
):
    return request_recovery(payload, request, db, "student", "verify")


@router.post("/reset-password")
def reset(payload: ResetInput, request: Request, db=Depends(get_db, scope="function")):
    if not svc.throttle(db, request, "consume-reset", maximum=10):
        return limited()
    if not svc.consume(db, payload.Token, "reset", payload.Password, "student"):
        return JSONResponse({"detail": "Invalid, expired, or previously used link."}, 400)
    return {"message": "Password changed. Sign in again with your new password."}


@router.post("/student/reset-password")
def student_reset(payload: ResetInput, request: Request, db=Depends(get_db, scope="function")):
    if not svc.throttle(db, request, "consume-reset:student", maximum=10):
        return limited()
    if not svc.consume(db, payload.Token, "reset", payload.Password, "student"):
        return JSONResponse({"detail": "Invalid, expired, or previously used link."}, 400)
    return {"message": "Password changed. Sign in again with your new password."}


@router.post("/admin/reset-password")
def admin_reset(payload: ResetInput, request: Request, db=Depends(get_db, scope="function")):
    if not svc.throttle(db, request, "consume-reset:admin", maximum=10):
        return limited()
    if not svc.consume(db, payload.Token, "reset", payload.Password, "admin"):
        return JSONResponse({"detail": "Invalid, expired, or previously used link."}, 400)
    return {"message": "Password changed. Sign in again with your new password."}


@router.post("/verify-email")
def verify(payload: TokenInput, request: Request, db=Depends(get_db, scope="function")):
    if not svc.throttle(db, request, "consume-verify", maximum=10):
        return limited()
    if not svc.consume(db, payload.Token, "verify", expected_role="student"):
        return JSONResponse({"detail": "Invalid, expired, or previously used link."}, 400)
    return {"message": "Email verified. You may now sign in."}


@router.get("/registration-groups")
def groups(chair_id: int, db=Depends(get_db, scope="function")):
    from app.student2.tables import TABLES as T

    g, sp, ch = T["StudentGroups"], T["Specializations"], T["Chairs"]
    stmt = (
        select(g.c.GroupID, g.c.GroupCode)
        .select_from(
            g.join(sp, g.c.SpecializationID == sp.c.SpecializationID).join(
                ch, sp.c.ChairID == ch.c.ChairID
            )
        )
        .where(
            ch.c.ChairID == chair_id,
            g.c.IsActive == True,
            sp.c.IsActive == True,
            ch.c.IsActive == True,
        )
        .order_by(g.c.GroupCode)
    )
    return {"items": [dict(row) for row in db.execute(stmt).mappings()]}


@router.post('/{role}/password-code')
def request_password_code(role: Literal['student', 'admin'],
                          payload: RecoveryRequestInput, request: Request,
                          db=Depends(get_db, scope='function')):
    from app.auth import reset_codes
    if not svc.throttle(db, request, 'password-code-request:'+role, payload.Email, 4):
        return limited()
    reset_codes.request_code(db, payload, role)
    local = get_settings().mail_backend == 'local'
    if payload.Language == 'en':
        message = ('If eligible, a 6-digit code was saved in the private local test mailbox; no email was sent.'
                   if local else 'If eligible, a 6-digit code was sent to your email.')
    else:
        message = ('Եթե հաշիվը համապատասխանում է, 6-նիշանոց կոդը պահպանվել է տեղային փորձնական փոստարկղում․ նամակ չի ուղարկվել։'
                   if local else 'Եթե հաշիվը համապատասխանում է, 6-նիշանոց կոդն ուղարկվել է ձեր էլփոստին։')
    return {'message': message}


@router.post('/{role}/verify-password-code')
def verify_password_code(role: Literal['student', 'admin'],
                         payload: ResetCodeInput, request: Request,
                         db=Depends(get_db, scope='function')):
    from app.auth import reset_codes
    if not svc.throttle(db, request, 'password-code-verify:'+role, payload.Email, 5):
        return limited()
    token = reset_codes.verify_code(db, payload, role)
    if not token:
        return JSONResponse({'detail': 'Invalid or expired code.'}, 400)
    return {'Token': token}

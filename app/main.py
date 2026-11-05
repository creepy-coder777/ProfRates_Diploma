from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from app.config import ROOT, get_settings
from app.database import get_engine, DatabaseNotConfigured
from app.security import require_admin
from app.student2.router import public, admin
from app.student2.dependencies import get_actor
from app.student3.router import router as student3

app = FastAPI(title="ProfRates — երկրորդ ուսանողի բաժին", version="0.3.0")

app.include_router(public)
app.include_router(admin)
app.include_router(student3)
from app.auth.router import router as session_router
from app.auth.admin import router as accounts_admin
app.include_router(accounts_admin)
app.include_router(session_router)

@app.get("/api/health/live", tags=["Առողջության ստուգում"])
def live():
    return {"status": "ok", "language": "hy", "stage": "student2"}

@app.get("/api/health/ready", tags=["Առողջության ստուգում"])
def ready():
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except DatabaseNotConfigured:
        raise HTTPException(503, "Բազայի միացումը դեռ կարգավորված չէ։") from None
    except Exception:
        # Չենք վերադարձնում connection string, օգտանուն կամ driver-ի ներքին սխալը։
        raise HTTPException(503, "SQL Server-ին միանալ չհաջողվեց։ Ստուգեք տեղային կարգավորումները։") from None
    return {"status": "ok", "database": "connected"}

@app.get("/api/admin/integration-status", dependencies=[Depends(get_actor)], tags=["Ինտեգրում"])
def integration_status():
    return {"status": "student2-implemented", "schema_source": "script.sql", "live_database_tested": False}

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/frontend/home_arm_guest.html")

# Միայն frontend պանակն է հրապարակվում, .env-ը և export-ները չեն մատուցվում։
app.mount("/frontend", StaticFiles(directory=ROOT / "frontend"), name="frontend")

# Reject browser cross-origin writes before authentication; require custom header
# for API mutations. Cookies are scoped and CSRF is tied to the server session.
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import secrets

@asynccontextmanager
async def lifespan(application):
    get_settings()  # Fail startup for unsafe production configuration.
    yield
app.router.lifespan_context = lifespan

@app.exception_handler(RequestValidationError)
async def validation_error(request, exc):
    # Pydantic's default includes input values (including submitted passwords).
    return JSONResponse({'detail':[{'loc':e['loc'],'msg':e['msg'],'type':e['type']} for e in exc.errors()]},422)

@app.middleware('http')
async def browser_security(request, call_next):
    if request.url.path.startswith('/api/') and request.method in {'POST','PUT','PATCH','DELETE'}:
        origin = request.headers.get('origin')
        if request.headers.get('sec-fetch-site') == 'cross-site' or (origin and origin.rstrip('/') != str(request.base_url).rstrip('/')):
            return JSONResponse({'detail':'Cross-origin request rejected.'},403)
        if request.url.path.startswith('/api/auth/') and request.headers.get('x-profrates-request') != '1':
            return JSONResponse({'detail':'Required request header missing.'},403)
        if request.cookies.get('pr_session'):
            header=request.headers.get('x-csrf-token','')
            cookie=request.cookies.get('pr_csrf','')
            if not header or not cookie or not secrets.compare_digest(header,cookie):
                return JSONResponse({'detail':'Invalid CSRF token.'},403)
    if request.url.path.startswith('/frontend/admin_portal/') and request.url.path.endswith('.html') and '/Admin_login_' not in request.url.path and '/account_recovery_' not in request.url.path:
        from app.auth.service import resolve_principal
        from starlette.concurrency import run_in_threadpool
        try:
            actor=await run_in_threadpool(resolve_principal,request)
            if not actor.is_admin:
                return JSONResponse({'detail':'Administrator account required.'},403)
        except HTTPException as exc:
            if exc.status_code==401:
                suffix='arm' if '_arm' in request.url.path else 'eng'
                return RedirectResponse('/frontend/admin_portal/Admin_login_'+suffix+'.html',303)
            return JSONResponse({'detail':exc.detail},exc.status_code)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    response.headers['X-Frame-Options']='DENY'
    if request.url.path.startswith('/api/') or '/account_recovery' in request.url.path:
        response.headers['Cache-Control']='no-store'
    return response

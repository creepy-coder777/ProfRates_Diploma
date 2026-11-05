from dataclasses import dataclass
from importlib import import_module
from typing import Annotated
from fastapi import Depends, HTTPException, Request
from app.config import get_settings

@dataclass(frozen=True)
class Principal:
    user_id: int | None
    is_admin: bool
    admin_id: int | None = None

def get_current_user(request: Request) -> Principal:
    provider = get_settings().auth_provider
    if not provider:
        from app.auth.service import resolve_principal
        return resolve_principal(request)
    # Optional pre-existing server-side integration. Never read identity from headers.
    try:
        module,name = provider.split(':',1)
        user = getattr(import_module(module),name)(request)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503,'Authentication service unavailable.') from None
    if not isinstance(user,Principal) or type(user.is_admin) is not bool:
        raise HTTPException(401,'Invalid authenticated identity.')
    for ident in (user.user_id,user.admin_id):
        if ident is not None and (type(ident) is not int or ident <= 0):
            raise HTTPException(401,'Invalid authenticated identity.')
    if user.is_admin and (user.admin_id is None or user.user_id is not None):
        raise HTTPException(401,'Invalid administrator identity.')
    return user

def require_admin(user: Annotated[Principal,Depends(get_current_user)]) -> Principal:
    if not user.is_admin:
        raise HTTPException(403,'Administrator access required.')
    return user

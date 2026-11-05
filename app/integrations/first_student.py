"""Bridge only: student-one middleware must supply a verified identity.
This adapter never reads a client-supplied role, user ID or admin ID.
"""
from fastapi import HTTPException,Request
from app.security import Principal


def resolve_principal(request:Request)->Principal:
    principal=getattr(request.state,'verified_profrates_principal',None)
    if not isinstance(principal,Principal) or type(principal.is_admin) is not bool:
        raise HTTPException(401,'Պահանջվում է մուտք գործել։')
    for ident in [principal.user_id,principal.admin_id]:
        if ident is not None and (type(ident)is not int or ident<=0):
            raise HTTPException(401,'Անվավեր նույնականացում։')
    return principal

import pytest
from starlette.requests import Request
from fastapi import HTTPException
from app.security import Principal
from app.integrations.first_student import resolve_principal


def test_bridge_rejects_request_headers_and_unverified_state():
    request=Request({'type':'http','headers':[(b'x-role',b'admin'),(b'x-admin-id',b'1')],'state':{}})
    with pytest.raises(HTTPException) as exc:resolve_principal(request)
    assert exc.value.status_code==401
    request.state.verified_profrates_principal={'is_admin':True,'admin_id':1}
    with pytest.raises(HTTPException):resolve_principal(request)


def test_bridge_only_accepts_verified_server_principal():
    request=Request({'type':'http','headers':[],'state':{}})
    principal=Principal(None,True,1);request.state.verified_profrates_principal=principal
    assert resolve_principal(request) is principal
    request.state.verified_profrates_principal=Principal(None,'false',1)
    with pytest.raises(HTTPException):resolve_principal(request)

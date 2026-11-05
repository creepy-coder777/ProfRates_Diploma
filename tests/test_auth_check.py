import json
from tools import check_auth

def test_real_auth_check_plan_does_not_save_credentials(tmp_path,monkeypatch):
    values=iter([(401,False),(401,False),(200,True)])
    monkeypatch.setattr(check_auth,'status',lambda *args,**kwargs:next(values))
    monkeypatch.setattr(check_auth.getpass,'getpass',lambda prompt:'local-secret-token')
    output=tmp_path/'report.json'
    assert check_auth.main(['--output',str(output)])==0
    text=output.read_text();assert 'local-secret-token'not in text
    assert json.loads(text)['writes'] is False

def test_auth_check_does_not_call_missing_provider_success(tmp_path,monkeypatch):
    monkeypatch.setattr(check_auth,'status',lambda *args,**kwargs:(401,False))
    monkeypatch.setattr(check_auth.getpass,'getpass',lambda prompt:'token')
    output=tmp_path/'report.json'
    assert check_auth.main(['--output',str(output)])==1
    assert json.loads(output.read_text())['status']=='failed'

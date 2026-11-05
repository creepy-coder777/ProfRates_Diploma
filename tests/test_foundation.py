from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app import main
from app.config import Settings
from app.database import connection_string, DatabaseNotConfigured
from app.security import Principal, get_current_user
from app.student2.dependencies import get_actor
import pytest

@pytest.fixture(autouse=True)
def reset_overrides():
    yield
    app.dependency_overrides.clear()

client = TestClient(app)

def test_live_and_default_armenian():
    assert client.get('/api/health/live').json()['language'] == 'hy'
    assert client.get('/').status_code == 200
    assert 'lang="hy"' in client.get('/frontend/backend_check.html').text

def test_admin_rejects_anonymous_and_forged_header():
    assert client.get('/api/admin/integration-status').status_code == 401
    assert client.get('/api/admin/integration-status', headers={'X-Role': 'admin', 'Authorization': 'Bearer fake'}).status_code == 401

def test_admin_rejects_student():
    app.dependency_overrides[get_current_user] = lambda: Principal(1, False)
    assert client.get('/api/admin/integration-status').status_code == 403

def test_verified_admin_contract():
    app.dependency_overrides[get_actor] = lambda: Principal(None, True, 1)
    assert client.get('/api/admin/integration-status').status_code == 200

def test_readiness_does_not_leak_secrets(monkeypatch):
    def broken():
        raise RuntimeError('PWD=private-secret;server=internal')
    monkeypatch.setattr(main, 'get_engine', broken)
    response = client.get('/api/health/ready')
    assert response.status_code == 503
    assert 'private-secret' not in response.text
    assert 'internal' not in response.text

def test_readiness_queries_database(monkeypatch):
    class Connection:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, query):
            assert str(query) == 'SELECT 1'
            return self
        def scalar_one(self): return 1
    class Engine:
        def connect(self): return Connection()
    monkeypatch.setattr(main, 'get_engine', lambda: Engine())
    assert client.get('/api/health/ready').json()['database'] == 'connected'

def test_no_configuration_fails_closed():
    with pytest.raises(DatabaseNotConfigured):
        connection_string(Settings(_env_file=None))

def test_odbc_password_escaping():
    s = Settings(_env_file=None, db_server='localhost', db_name='ProfRates', db_trusted_connection=False,
                 db_user='user', db_password='x};Trusted_Connection=yes;')
    assert 'PWD={x}};Trusted_Connection=yes;}' in connection_string(s)

def test_secrets_not_served():
    for path in ['/frontend/.env', '/.env', '/exports/schema_metadata.json']:
        assert client.get(path).status_code == 404

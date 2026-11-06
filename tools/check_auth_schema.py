"""Read-only account metadata check. No migrations or data writes."""
from sqlalchemy import inspect
from app.database import get_engine

REQUIRED = {
    'Admins': {'IsEmailVerified'},
    'PasswordResets': {'Code','UserID','AdminID','Purpose','Expiry','IsUsed'},
    'AuthSessions': {'SessionHash','CSRFHash','UserID','AdminID','CreatedAt','ExpiresAt'},
    'AuthRateLimits': {'KeyHash','WindowStart','Attempts'},
}

def column_problems(name, actual):
    issues = []
    missing = sorted(REQUIRED[name] - actual.keys())
    if missing:
        issues.append(name + ': missing columns: ' + ', '.join(missing))
    if name == 'PasswordResets':
        if 'Code' in actual:
            typ = actual['Code']['type']
            length = getattr(typ, 'length', None)
            if not hasattr(typ, 'length') or (length is not None and length != -1 and length < 64):
                issues.append('PasswordResets.Code: string storage of at least 64 characters required')
        if 'UserID' in actual and not actual['UserID']['nullable']:
            issues.append('PasswordResets.UserID: must allow NULL for administrator recovery')
    return issues

def main():
    try:
        inspector = inspect(get_engine())
        names = set(inspector.get_table_names(schema='dbo'))
        problems = []
        for name in REQUIRED:
            if name not in names:
                problems.append('Missing table: dbo.' + name)
                continue
            actual = {c['name']: c for c in inspector.get_columns(name, schema='dbo')}
            problems.extend(column_problems(name, actual))
        if problems:
            print('ACCOUNT SCHEMA: CHECK REQUIRED')
            for problem in problems:
                print('CHECK: ' + problem)
            print('No database changes made. Compare the findings before applying migration 03 (04 is legacy and not required).')
            return 1
        print('Account migration structure is present. Runtime behavior still requires tests.')
        return 0
    except Exception:
        print('Cannot inspect account metadata. Check the connection and metadata permissions.')
        print('No database changes made.')
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

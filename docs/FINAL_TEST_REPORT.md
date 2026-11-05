# Final verification report — 2026-10-23

## Executed results

| Check | Actual result |
|---|---|
| Final full pytest collection | **100 passed, 0 failed**, 1 dependency deprecation warning; 213.05 s |
| Initial new authentication subset | 29 passed before adding the additional edge-case tests |
| First full run | 97 passed, 1 failed; an existing test passed the DB argument as the language argument to rankings |
| Correction | Test call changed to rankings(db=db); application ranking implementation unchanged |
| Final Python/JavaScript syntax | See final_syntax_results.json |
| SQL Server localhost connection | Failed: server/instance inaccessible or not found |
| SQL Server configured instance connection | Failed: instance lookup/login timeout |
| Migration 03 execution/rerun on SQL Server | **NOT EXECUTED** |
| Real SQL Server auth / FK / trigger / concurrency tests | **NOT EXECUTED** |
| Actual external SMTP message | **NOT SENT / NOT TESTED** — credentials unavailable |
| SMTP delivery component | Unit tested with fake SMTP transport: TLS configured and recipient passed correctly |
| Full visual/browser interaction | **NOT EXECUTED** — syntax and wiring checks are not browser E2E |

Machine-readable final pytest output: final_pytest_results.xml.
Installed dependency versions: final_test_environment.json.

## Test environment and the transport limitation

Python 3.13.5 on a restricted Windows execution host.
Ordinary pytest attempts first encountered an unwritable default temporary folder and then a Windows
asyncio TCP socketpair startup hang before reaching the application. An IOCP-only wakeup shim was used
to run the final suite with the original FastAPI/Starlette TestClient.

The exact environment-only runner is preserved as verification/sandbox_test_runner.py.
It replaces event-loop wakeup plumbing, not routes, authorization, password verification, token logic,
request middleware or responses. The original TestClient and actual ASGI application were used.
The earlier unsuccessful ASGI-client alternative was not used for the successful final result.
The final command was equivalent to:

```powershell
python -X utf8 docs/verification/sandbox_test_runner.py . -q --tb=short --basetemp=tests_tmp_final01 --junitxml=docs/final_pytest_results.xml
```

On the user's ordinary machine, first use the standard documented `python -X utf8 -m pytest -q`.
The environment-only runner is evidence/reproduction support, not an application startup component.

Tests use a fresh SQLite database with the project's table mappings and test-specific rating views/triggers.
They execute real account SQL queries, route dependencies, middleware and password/token behavior.
SQLite does not validate SQL Server-specific DDL, FK/index alterations, stored procedures or lock behavior.
Some pre-existing tests intentionally override Principal for testing existing administrative business logic;
the new account tests do not replace credential verification or role checks.

## Coverage added

- Password hashes salted independently; valid/invalid/legacy malformed hashes.
- Successful and duplicate registration; invalid domain, names, group, chair and privilege-injection fields.
- Unverified login denial, verification expiry/resend/replay, successful login and unknown/wrong credentials.
- Session expiry, logout invalidation and protected endpoints.
- Student/admin separation, forged role/identity headers rejected, cross-user access guarded.
- Administrator dashboard, user listings/status changes, safe reset-history/audit projections and protected HTML.
- Generic recovery responses for known/unknown addresses.
- Local private mailbox, hashed token storage, invalid/expired/reused/wrong-purpose tokens.
- New password accepted and old password rejected; previous sessions revoked.
- CSRF/origin protection, persistent rate limits and sanitized validation/database errors.
- Production forbids local mailbox and insecure cookies/base URL; no token-mailbox HTTP endpoint.
- Mail delivery failures audited without publicly claiming delivery; fake SMTP TLS unit test.
- Existing Student2/Student3 regression tests and schema-verifier tests retained.

## Required external acceptance

1. Compare actual SQL Server metadata and existing rating-view definitions to the supplied SQL files.
2. Back up the existing database and manually apply 03_auth_accounts.sql.
3. Run check_db, check_auth_schema, verify_schema and the pre-existing Student3 checks.
4. Run tools.smoke_auth_mssql --confirm-test-writes, optionally with --admin-email.
5. Complete Scenario A in FINAL_GUIDE_HY.md in the browser.
6. Configure an independent SMTP provider and complete Scenario B only with valid credentials.
7. Verify production TLS/reverse-proxy/cookie configuration and least-privilege database permissions.

These external checks remain outstanding. The report does not certify full security or live production readiness.

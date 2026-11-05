# Implementation summary

## Implemented

- Real student registration against Users and existing group/specialization/chair relationships.
  The @polytechnic.am restriction is enforced in student registration and login schemas; all students require email verification.
- PBKDF2-SHA256 password hashing, per-password salts, database-backed opaque sessions,
  logout/session revocation, strict same-site cookies and session-bound CSRF checks.
- Strict request schemas reject extra role/ID/verification fields. Backend validates active/verified student state on protected requests.
- Existing Admins and Users tables retain separate roles; no duplicate role system or public administrator registration exists.
- Hashed, expiring, single-use verification/reset tokens reuse PasswordResets.
  Password reset invalidates other reset links and all previous sessions for that account.
- Mailer protocol with a private development file mailbox and configurable TLS SMTP implementation.
  No mailbox/token-viewing HTTP endpoint exists; production rejects local mail configuration.
- Database rate limits for login, registration, recovery and token consumption.
- Existing ActivityLogs reused for success/failure events, anonymous attempts, mail delivery outcomes,
  account creation/status changes, password changes and administrator operations.
- Administrator dashboard, safe student account listings/exports/updates/status changes,
  audit listings, reset history and reset requests connected to the original HTML layouts.
- Original professor/question/academic/moderation/rating endpoints remain in use.
- Administrator bootstrap, offline recovery and email-verification CLI commands.
- Safe sample configuration, manual migration, read-only schema check, live SQL Server acceptance command,
  automated tests and separate local/SMTP demonstration instructions.

## Important choices

- Registration now requires GroupID as well as ChairID. The original form asked only for a chair,
  but Users has GroupID and no ChairID. Existing active groups are loaded rather than guessing a group.
- Public registration creates only student accounts; account role, verification flag, email changes and password hashes
  cannot be set by the administrator's ordinary student-edit endpoint.
- The old “Add user” control opens the real student registration form. It does not silently invent a password
  or create a privileged account.
- The dashboard uses COUNT/AVG queries and the existing SQL rating view; no rating formula is reimplemented in Python.
- Administrator email reset requires the new verified flag. Trusted local DB operators retain a documented recovery path.
- Anonymous events use NULL audit actors with the target account ID when known. They do not falsely identify
  a failed caller as an authenticated account owner.
- The input ZIP contains duplicate patch payloads and UI backups. The deliverable contains the main runnable project,
  with working source/assets preserved and obsolete machine-specific/runtime files omitted.

## Not asserted / still requires local validation

- SQL Server connections failed here. Migration 03 execution, rerun behavior, constraints/FKs,
  concurrent reset consumption, SQL Server trigger behavior and true end-to-end SQL Server authentication
  must be verified with the provided commands on the actual machine.
- Actual SMTP acceptance/delivery requires valid external service credentials and has not been performed.
  The SMTP component's TLS configuration can be unit-tested using a fake server; that is not real email delivery.
- Browser interaction and visual rendering of all pages have not been tested end to end.
  Python/JavaScript syntax and HTML/script wiring are checked separately.
- Real university enrollment/identity validation is outside the available data; development mailbox links
  prove the demo workflow, not ownership of an actual university email.
- Legacy sample hashes in the original export require reset; a working password is never guessed.
- The original .bak could not be examined and is not part of the cleaned runnable ZIP.
  No live data has been migrated, reseeded, reset or deleted during this work.
- This deliverable is implemented and locally testable; final production readiness and the user's live
  SQL Server acceptance criteria remain conditional on those external checks.

See FINAL_GUIDE_HY.md, DATABASE_CHANGES.md, ENDPOINTS.md, CHANGED_FILES.json and FINAL_TEST_REPORT.md.

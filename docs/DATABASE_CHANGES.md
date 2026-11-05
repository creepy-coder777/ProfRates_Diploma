# Database changes and evidence

## Evidence reviewed

- `database/01_original_export.sql`: the supplied UTF-16 SQL Server export, including table definitions,
  keys, defaults, indexes, check constraints, foreign keys, views, 932 data INSERT statements and stored procedures.
- `database/02_upgrade_student3.sql`: the pre-existing reaction trigger and rating-view migration.
- `docs/verified_schema.json`, `docs/schema_contract.json`: pre-existing explicit mappings/contracts.
- `app/student2`, `app/student3`: consumers of those objects.
- Live connections attempted to localhost and the supplied configured instance; both timed out.
  Live sys.* metadata and the contents of the historical .bak could NOT be inspected here.
  The .bak's correspondence to the SQL export is unconfirmed.

Original export views: vwRatingScores, vwLecturerRatingSummary, vwStudentCurrentSemester,
vwNPUACurriculum, vw_StudentGroups, vw_Ratings_Public, vw_Ratings_OwnUser, vw_Ratings_Admin,
vwAcademicTerms, vwLecturerTermRatingSummary.
Stored procedures: uspLecturerRankings, uspSetStudentCurrentSemester.
The original export has no CREATE TRIGGER; 02 adds tr_RatingReactions_Counters.
The unchanged SQL views/procedures remain the source of rating calculations and academic-semester rules.

## Why migration 03 is necessary

| Existing object | Minimal change | Reason and data preservation |
|---|---|---|
| PasswordResets.Code | varchar(10) → varchar(64) | Store SHA-256 of a random 256-bit bearer token; old values remain unchanged |
| PasswordResets.UserID | allow NULL | An administrator token has AdminID instead of a student ID |
| PasswordResets | add AdminID nullable FK to Admins | Reuse reset storage for existing separate administrator accounts |
| PasswordResets | add Purpose with legacy for existing rows | Distinguish reset/verify; pre-existing codes are never accepted by new endpoints |
| PasswordResets | add exactly-one-account and purpose checks | A token cannot target two accounts or ambiguous operations |
| Admins | add IsEmailVerified bit default 0 | Do not assume administrator email ownership; verified email is required for email reset |
| ActivityLogs | replace named actor check with at-most-one actor | Retain existing log; unknown-account attempts use NULL actors, known users/admins retain their IDs |
| AuthSessions | new table + owner indexes/FKs/check | Hashed revocable opaque session IDs and hashed CSRF tokens, with expiry |
| AuthRateLimits | new table | Hashed IP/email keys and fixed-window counters shared across application workers |

No role table is added: Users are students; Admins are administrators, exactly as in the supplied schema.
No public role-changing API exists. No users/admins are deleted by the migration.
No rating columns, score formulas, views, stored procedures or reaction triggers are changed.
The audit actor constraint change intentionally permits anonymous/system events without creating a fake account.

## Application and recovery procedure

Take a SQL Server backup; inspect live metadata first. Execute 03 manually in SSMS with
ProfRates_databaza selected, then run `python -m tools.check_auth_schema` and
`python -m tools.verify_schema`. Startup never executes DDL.
03 uses XACT_ABORT and an explicit transaction, and checks the database name and original required tables.
Case-insensitive duplicate emails abort before any DDL; they are not silently merged or deleted.
Repeated execution retains data and skips existing columns/tables.
Unexpected existing custom objects/constraints or column types require manual comparison, not forced replacement.
The script's DDL, rerun behavior and lock contention have NOT been executed against SQL Server in this environment.

Rollback is a DBA operation using the backup/verified change plan; no automatic DROP rollback is supplied,
because it would discard new session/token data. Do not revert the enlarged Code column to varchar(10)
once 64-character token hashes exist. Deploy code and migration together.

## Transaction behavior and permissions

Writes use the existing SERIALIZABLE dependency. Token consumption uses a conditional IsUsed/expiry UPDATE,
and session invalidation occurs in the same transaction as password updates.
A serialization conflict/deadlock yields a generic 503/409 and may require a retry; SQL Server concurrency
still needs local verification. Rate-limit failures and failed login audit events return HTTP responses
without raising an exception, so their counters/audit commit.

Queries use SQLAlchemy parameters. No client-supplied identifier is interpolated into raw SQL.
The database owner performs migrations. The runtime account needs only the table/view/procedure permissions
required by the implemented features; it does not need CREATE/DROP permissions.
Restrict ActivityLogs to SELECT/INSERT at runtime and grant management of SQL permissions only to the DBA.
Users cannot read password hashes, reset token hashes or session hashes through the public/admin projections.

All newly written auth times are UTC naive values suitable for the original datetime columns.
Pre-existing historical audit timestamps used the database's local time; no unsafe bulk time conversion is attempted.


## Existing score-source discrepancy (not changed here)

The original export's vwLecturerRatingSummary and vwLecturerTermRatingSummary filter Approved ratings.
The pre-existing 02 migration removes those Approved filters.
Without live metadata, the actual deployed definition cannot be established.
This is why 02 must not be reapplied automatically and why the verifier reports text differences.
The team must confirm its final rule before changing either view. No new coefficients or ranking formula are introduced here.
The dashboard's new average is explicitly the SQL AVG of OverallScore over the existing admin view (all statuses);
it is a platform statistic, not the lecturer ranking or a replacement for the stored procedure.

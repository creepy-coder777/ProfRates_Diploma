# API endpoints

This is the actual registered route list. /docs contains request/response schemas.
For POST/PUT/PATCH/DELETE from the web UI, api.js supplies the required request header and cookie-bound CSRF token.

| Method | Path | Access |
|---|---|---|
| GET | `/api/lecturers` | Public |
| GET | `/api/lecturers/{ident}` | Public |
| GET | `/api/questions` | Public |
| GET | `/api/academic/{resource_name}` | Public |
| GET | `/api/lecturers/{ident}/comments` | Public |
| GET | `/api/admin/lecturers/export` | Administrator |
| GET | `/api/admin/lecturers` | Administrator |
| POST | `/api/admin/lecturers` | Administrator |
| PUT | `/api/admin/lecturers/{ident}` | Administrator |
| DELETE | `/api/admin/lecturers/{ident}` | Administrator |
| GET | `/api/admin/questions/export` | Administrator |
| GET | `/api/admin/questions` | Administrator |
| POST | `/api/admin/questions` | Administrator |
| PUT | `/api/admin/questions/order` | Administrator |
| PUT | `/api/admin/questions/{ident}` | Administrator |
| DELETE | `/api/admin/questions/{ident}` | Administrator |
| GET | `/api/admin/academic/catalog` | Administrator |
| GET | `/api/admin/academic/{resource_name}/export` | Administrator |
| GET | `/api/admin/academic/{resource_name}` | Administrator |
| POST | `/api/admin/academic/{resource_name}` | Administrator |
| PUT | `/api/admin/academic/{resource_name}/{ident}` | Administrator |
| DELETE | `/api/admin/academic/{resource_name}/{ident}` | Administrator |
| GET | `/api/admin/semesters` | Administrator |
| GET | `/api/admin/student-options` | Administrator |
| GET | `/api/admin/student-courses/export` | Administrator |
| GET | `/api/admin/student-courses` | Administrator |
| POST | `/api/admin/student-courses` | Administrator |
| DELETE | `/api/admin/student-courses/{ident}` | Administrator |
| PUT | `/api/admin/courses/{ident}/lecturer` | Administrator |
| GET | `/api/admin/comments/export` | Administrator |
| GET | `/api/admin/comments` | Administrator |
| PUT | `/api/admin/comments/{ident}/moderation` | Administrator |
| GET | `/api/admin/rating-queue` | Administrator |
| GET | `/api/admin/lecturers/{ident}/rating-statistics` | Administrator |
| GET | `/api/me/rating-options` | Student / endpoint-specific |
| GET | `/api/me/ratings` | Student / endpoint-specific |
| GET | `/api/me/ratings/{ident}` | Student / endpoint-specific |
| POST | `/api/ratings` | Student / endpoint-specific |
| GET | `/api/me/ratings/{ident}/questions` | Student / endpoint-specific |
| PUT | `/api/ratings/{ident}` | Student / endpoint-specific |
| DELETE | `/api/ratings/{ident}` | Student / endpoint-specific |
| GET | `/api/lecturers/{ident}/ratings` | Public |
| GET | `/api/lecturers/{ident}/statistics` | Public |
| GET | `/api/ratings/{ident}/like` | Student / endpoint-specific |
| PUT | `/api/ratings/{ident}/like` | Student / endpoint-specific |
| DELETE | `/api/ratings/{ident}/like` | Student / endpoint-specific |
| GET | `/api/ratings/{ident}/reaction` | Student / endpoint-specific |
| DELETE | `/api/ratings/{ident}/reaction` | Student / endpoint-specific |
| PUT | `/api/ratings/{ident}/dislike` | Student / endpoint-specific |
| DELETE | `/api/ratings/{ident}/dislike` | Student / endpoint-specific |
| GET | `/api/rankings` | Public |
| GET | `/api/admin/users` | Administrator |
| GET | `/api/admin/users/export` | Administrator |
| PUT | `/api/admin/users/{ident}` | Administrator |
| GET | `/api/admin/activity-logs` | Administrator |
| GET | `/api/admin/password-resets` | Administrator |
| POST | `/api/admin/password-resets` | Administrator |
| GET | `/api/admin/dashboard` | Administrator |
| POST | `/api/auth/register` | Public |
| POST | `/api/auth/login` | Public |
| POST | `/api/auth/admin/login` | Public |
| GET | `/api/auth/session` | Authenticated session |
| POST | `/api/auth/logout` | Authenticated session |
| POST | `/api/auth/student/forgot-password` | Public, student accounts only |
| POST | `/api/auth/admin/forgot-password` | Public, administrator accounts only |
| POST | `/api/auth/forgot-password` | Public, compatibility alias restricted to student accounts |
| POST | `/api/auth/resend-verification` | Public |
| POST | `/api/auth/student/resend-verification` | Public, unverified active student accounts only |
| POST | `/api/auth/student/reset-password` | Public, one-time student reset token |
| POST | `/api/auth/admin/reset-password` | Public, one-time administrator reset token |
| POST | `/api/auth/reset-password` | Public, compatibility alias restricted to student reset tokens |
| POST | `/api/auth/verify-email` | Public |
| GET | `/api/auth/registration-groups` | Public |
| GET | `/api/health/live` | Public |
| GET | `/api/health/ready` | Public |
| GET | `/api/admin/integration-status` | Administrator |

## New account and dashboard operations

- POST /api/auth/register: student only; requires a real active group and matching chair, creates unverified account.
- POST /api/auth/login and /api/auth/admin/login: verify credentials and issue opaque session/CSRF cookies.
- GET /api/auth/session: current server-verified role. POST /logout: revoke current session.
- Student/admin recovery requests use distinct endpoints and return the same generic eligibility response within each delivery mode; never return token.
- Reset endpoints verify both token purpose and the account role recorded with the token; mismatches return 400 without consuming the token.
- POST /api/auth/resend-verification and /verify-email: student-only verification action and one-time token.
- GET /api/auth/registration-groups: active real groups for selected chair.
- GET /api/admin/dashboard: counts, admin profile, recent events, pending reviews and all-rating SQL average.
- GET /api/admin/users and /users/export: safe projection without password/token hashes.
- PUT /api/admin/users/{ident}: name, group and Active/Suspended/Banned status, never role or email ownership.
- GET /api/admin/activity-logs: read-only paginated audit list.
- GET /api/admin/password-resets: safe history without Code. POST: request delivery to eligible account.

Expected errors: 401 anonymous/invalid session; 403 wrong role/CSRF/origin; 409 duplicate/conflict; 422 validation; 429 rate limited; 503 database/configuration unavailable.
Administrator bootstrap and operator-controlled recovery overrides remain LOCAL CLI commands. Public admin recovery only issues a one-time link to an eligible administrator account; it never changes a password without that token. The private test mailbox remains a local-only tool.

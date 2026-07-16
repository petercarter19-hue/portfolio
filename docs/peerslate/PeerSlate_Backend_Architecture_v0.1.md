# PeerSlate Backend Architecture v0.1

**Status:** Local implementation complete; production authentication and deployment not enabled
**Date:** July 10, 2026
**Scope:** Effort 6 database service, identity boundary, APIs, UI adapters, and verification

## 1. Implemented Outcome

PeerSlate's Flask application now connects to the existing Azure SQL backend through a reusable service layer. API routes call stored procedures with bound parameters, derive tenant ownership from a trusted server-side identity, return named JSON structures, and keep raw database errors out of normal API responses.

The current public pages remain unchanged by default. Database-backed Board, Daily Slate, and Break behavior is available only when `PEERSLATE_DATABASE_UI_ENABLED=true` and a trusted member identity is present.

## 2. Runtime Flow

1. Azure App Service Easy Auth validates the member before the request reaches Flask.
2. App Service injects `X-MS-CLIENT-PRINCIPAL`, containing Base64-encoded identity claims.
3. `identity.py` accepts that header only when `PEERSLATE_TRUST_EASYAUTH_HEADERS=true`; Azure hosting and Flask test mode alone are not trusted boundaries.
4. `dbo.usp_UpsertAppUserFromAuth` creates or updates the member and returns the database-owned `user_key`.
5. API code uses that `user_key`; browser query strings and JSON bodies cannot select another tenant.
6. `DatabaseService` calls an allow-listed stored-procedure-shaped name with parameter binding.
7. SQL procedures enforce ownership again through `user_id` or `user_key` filters.
8. The API serializes dates, decimals, and binary values into JSON-safe forms.

## 3. Code Map

| File | Responsibility |
| --- | --- |
| `db.py` | Loads the protected connection string, normalizes connector compatibility, opens Azure SQL connections, and serializes result sets. |
| `services/database_service.py` | Central stored-procedure execution, parameter-name validation, cleanup, first-row helpers, and named result-set mapping. |
| `identity.py` | Easy Auth claim decoding, stable subject selection, member upsert, and explicit local-development identity. |
| `peerslate_api.py` | Authenticated dashboard, feed, save, poll, challenge, journal, Slate Board, badge, and achievement APIs. |
| `app.py` | Application configuration, blueprint registration, feature flags, and temporary connectivity endpoints. |
| `static/js/slate-board.js` | Browser-storage preview by default; private SQL-backed Board entries behind the database UI flag. |
| `static/js/the-slate.js` | Browser-storage preview by default; private SQL-backed Daily Slate entries behind the database UI flag. |
| `static/js/break-database.js` | Loads current Break cards and poll options; records challenge, vote, and save actions when enabled. |

## 4. API Map

All write requests require JSON where a body is present and the header `X-PeerSlate-Request: same-origin`.

| Method | Route | Stored procedure |
| --- | --- | --- |
| GET | `/api/dashboard` | `usp_GetPeerSlateUserDashboard` |
| GET | `/api/feed/break` | `usp_GetTodayBreakFeedForUser` |
| POST | `/api/feed/interactions` | `usp_RecordFeedInteraction` |
| GET | `/api/saved-boards` | `usp_GetUserBoardContents` |
| POST/DELETE | `/api/saved-boards/<board>/items/<content>` | `usp_SaveContentToBoard` / `usp_UnsaveContentFromBoard` |
| GET | `/api/polls/today/options` | `usp_GetTodayBreakPollOptions` |
| POST | `/api/polls/<poll>/votes` | `usp_SubmitPollVote` |
| GET/POST | `/api/challenges` and `/api/challenges/<content>/complete` | Challenge progress/history/completion procedures |
| GET/POST | `/api/journal/*` | Today, history, and save journal procedures |
| GET | `/api/slate-spaces/<name>` | `usp_GetSlateSpaceForUser` |
| POST/PATCH | `/api/slate-items` and `/api/slate-items/<id>` | Add/update Slate item procedures |
| POST/DELETE | `/api/slate-items/<id>/links*` | Link/unlink procedures |
| POST | `/api/slate-items/<id>/archive` or `/restore` | Archive/restore procedures |
| GET | `/api/badges` | `usp_GetUserBadges` |
| POST | `/api/achievements/evaluate` | `usp_EvaluateUserFlatAchievements` |

The dashboard's eight result sets are named: `user_summary`, `today_break_feed`, `today_poll_options`, `recent_badges`, `achievement_progress`, `saved_boards`, `slate_spaces`, and `challenge_progress`.

## 5. Identity Modes

### Production target

- Enable Azure App Service Authentication and require sign-in.
- Permit Flask to trust Easy Auth headers only when requests cannot bypass App Service authentication.
- Verify direct client-supplied `X-MS-CLIENT-PRINCIPAL` headers are removed or rejected, then explicitly set `PEERSLATE_TRUST_EASYAUTH_HEADERS=true`.
- Keep `PEERSLATE_ALLOW_DEV_IDENTITY=false`.
- Do not set `PEERSLATE_DEV_USER_KEY` as a production identity mechanism.

### Local development

Set both values explicitly:

```text
PEERSLATE_ALLOW_DEV_IDENTITY=true
PEERSLATE_DEV_USER_KEY=test-user-1
```

The local user is a fixture identity only. It does not prove production authentication.

## 6. Feature Flags

| Variable | Default | Purpose |
| --- | --- | --- |
| `PEERSLATE_DATABASE_UI_ENABLED` | `false` | Enables SQL-backed Board, Daily Slate, and Break behavior. |
| `PEERSLATE_LIVING_RESUME_DB_ENABLED` | `false` | Enables the owner/public Living Resume read APIs after PS-PLAT-006 and PS-PLAT-007 verification. |
| `PEERSLATE_ENABLE_DB_TEST_ROUTES` | `false` | Enables temporary raw connectivity routes locally. Keep off in production. |
| `PEERSLATE_ALLOW_DEV_IDENTITY` | `false` | Allows the configured development user. Never enable in production. |
| `PEERSLATE_TRUST_EASYAUTH_HEADERS` | `false` | Explicitly enables Easy Auth header processing after the trusted boundary is configured and bypass-tested. Azure hosting is not sufficient by itself. |

## 7. Security Properties

- API routes never accept a browser-provided `user_key`.
- SQL values use positional binding.
- Stored procedure and parameter identifiers are validated before statement construction.
- Write routes require a non-simple same-origin header to reduce cross-site request risk.
- New Board and Daily Slate records are private; publishing is not implied or automated.
- Normal API errors do not return raw database exceptions.
- `.env` and `.env.*` remain ignored by Git.
- Temporary diagnostic routes are disabled by default.

Before production, add an explicit origin policy, production-grade rate-limit storage, security headers, centralized request IDs, and structured secret-safe logging.

## 8. Current Database Domains

The database currently supports:

- auth-ready users;
- daily feed content and interactions;
- saved content boards;
- polls and votes;
- challenges and completions;
- journal responses;
- Slate Spaces, items, progress, and links;
- application events, achievements, and badges.

It does not yet contain the PS-FEAT-001 Living Resume entities. Those require a separately reviewed migration.

## 9. Fixture-Only and Deferred Behavior

- `test-user-1` is development fixture data only.
- Pete-specific visible Board cards and profile copy remain presentation fixtures; new API-created items are generic and tenant-owned.
- Production sign-in is not configured by these code changes.
- Admin content editing is not implemented because admin stored-procedure contracts and authorization policy do not yet exist.
- Public publishing is intentionally deferred; the current database flow defaults new content to private.
- No migration, deployment, merge, or production configuration change was performed.

## 10. Verification

Run:

```powershell
.\venv\Scripts\python.exe -m py_compile app.py db.py identity.py peerslate_api.py services\database_service.py
.\venv\Scripts\python.exe -m unittest discover -s tests -v
```

For local live testing, enable the development identity and database UI flags for that process, start `python app.py`, then check the APIs and updated pages. Use `SQL FIles/Verification/peerslate_backend_health_check.sql` for a read-only database inventory.

Verified on July 10, 2026:

- 11 unit and security tests passed;
- 14 write-procedure paths passed inside a rollback-only transaction;
- rollback preserved the original Slate item count;
- all required procedures were present;
- nine live read APIs returned success;
- preserved public pages returned HTTP 200;
- Board, Break, and Daily Slate passed desktop and mobile checks without horizontal overflow.

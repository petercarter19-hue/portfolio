# Verification evidence

## Completed locally

```powershell
# Run with the repository's non-secret local test placeholder configured.
.\.venv\Scripts\python.exe -m unittest tests.test_owner_capture tests.test_sql_foundation -v
```

Result on 2026-07-17: the final focused capture and migration suites passed
19 tests; the broader focused capture/foundation pass had previously passed 28.

```powershell
.\.venv\Scripts\python.exe scripts\apply_sql_migrations.py --migration PS-CAPTURE-001
```

Result: printed only `PS-CAPTURE-001_captures.sql` and reported plan-only; no
database changes were made.

```powershell
.\.venv\Scripts\python.exe -m unittest tests.test_site_rules -v
.\.venv\Scripts\python.exe -m unittest discover -s tests -q
.\.venv\Scripts\python.exe -m compileall -q owner_routes.py services tests scripts
git diff --check
```

Results: 8/8 guardrails passed, all 252 tests passed, compilation succeeded,
and the diff contained no whitespace errors. The expected Flask-Limiter local
in-memory warning remains unchanged.

## Browser review

- Desktop 1440x900: 880px capture panel, no horizontal overflow.
- Mobile 390x844: responsive panel/textarea, long content wraps, no horizontal
  overflow.
- Exactly one main landmark and one `#main-content` skip-link target.
- Textarea label, 8,000-character limit, cyan visible focus outline, and 44px
  submit target verified.
- Real local form POST redirected to `?saved=1` and exposed the accessible
  `Saved privately.` status. The preview used in-memory synthetic data only.
- Reduced-motion media rule is present. The 390 CSS-pixel reflow check is
  stricter than a 200% zoom check on a 1280px-wide desktop viewport.

## Prerequisite release

Settings prerequisite pipeline run 74 (`20260717.7`) succeeded for exact merge
commit `086753f2e1df2fb02dfd55a51d41b35d12fcc431`.

## Migration attempt record

The first approved apply attempt reached Azure SQL but failed during parsing
because SQL Server does not accept inline `CONCAT(...)` as a stored-procedure
argument. The outer migration transaction rolled back. A read-only follow-up
confirmed `capture_table=0`, `migration_record=0`, and
`capture_procedures=0`. The migration now assigns the metadata JSON to a local
variable before calling the audit procedure; focused tests passed again before
retry.

The corrected retry used the reviewed runner with `--migration PS-CAPTURE-001
--apply --verify` and the approved machine-local environment file. Result:

- `PS-CAPTURE-001_captures.sql` applied successfully.
- All eight foundation migration records, expected platform/career/identity
  objects, tenant constraints, private profile defaults, and discovery defaults
  verified.
- Two synthetic owners and captures passed the real owner-isolation checks.
- The verification transaction rolled all synthetic users, identities,
  profiles, preferences, captures, and audit events back.

No connection string or private member content was printed or recorded.

## Azure application release

- Azure DevOps PR 56 reviewed source
  `4cfbd8e234bb56b004eb0d6feece88eec3b6d969` against Settings baseline
  `086753f2e1df2fb02dfd55a51d41b35d12fcc431`.
- PR 56 completed with squash merge and remote branch deletion.
- Production merge: `af3547796966628da1672256a332e3b874750c7f`.
- Automatic pipeline run 75 (`20260717.8`) used that exact source version.
- Build completed successfully at `2026-07-17T19:49:38Z`.
- Deploy completed successfully at `2026-07-17T19:51:54Z`.
- A redundant not-started manual fallback run 76 was canceled after the delayed
  automatic trigger became visible; it never deployed.
- App Service deployment history marks merge `af354779...`, build 75, and the
  production slot active and complete.

The first request after deployment returned the previous worker's 404 even
though the exact deployment record was active. Restarting only the
`peerslate-pete` App Service loaded the deployed route table. Final checks:

```text
Azure hostname /app/capture -> 302 /auth/sign-in?return_to=/app/capture
https://peerslate.com/app/capture -> 302 /auth/sign-in?return_to=/app/capture
https://peerslate.com/app/settings -> 302 /auth/sign-in?return_to=/app/settings
https://peerslate.com/ -> 200
```

The in-app browser followed the production Capture route to the real PeerSlate
member sign-in page. A real member capture was intentionally not created because
this slice does not yet provide delete UI; the live stored procedures and
owner-isolation behavior were instead verified with synthetic transactional
data that was fully rolled back.

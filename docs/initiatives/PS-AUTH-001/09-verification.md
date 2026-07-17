# PS-AUTH-001 verification

- Baseline: `python -m unittest discover -s tests -q` — 212 tests passed.
- Final: `python -m unittest discover -s tests -q` — 221 tests passed.
- Dependencies: `python -m pip check` — no broken requirements.
- Local browser: desktop homepage and sign-in fallback rendered; mobile sign-in
  rendered without horizontal overflow after correcting panel box sizing.
- SQL baseline: production had PS-PLAT-001 through PS-PLAT-005 only.
- Forward SQL dry run: PS-PLAT-006, PS-PLAT-007, PS-AUTH-001 — passed inside an outer rollback transaction.
- Reverse rollback dry run — passed.
- Production SQL apply — all eight migrations passed read-only verification.
- SQL integration: two distinct identities, returning identity, private profiles, and all discovery flags off — passed inside a rollback transaction; no test rows remained.
- Live pre-deploy: `/api/dashboard` returns 401 for anonymous requests; `/.auth/me` is not configured yet.

Remaining verification after Azure setup: Google sign-in, email sign-in, logout,
session expiry, two separate real accounts, and production `/app` rendering.

# Slice 1-2 Implementation Brief — Access Boundary + Storage Isolation

You are the sole implementation writer for `PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001`,
working ONLY in the implementation worktree you are given. Architecture authority: the accepted
deliverable in `C:\Users\peter\iCloudDrive\PeerSlate Architect Handoffs\2026-08-11\Interview Studio
Claude Architecture Deliverable 2026-08-11\` (files 02, 04, 07 govern these slices). Line numbers
below refer to current origin/main and may shift slightly; verify before editing.

## Hard rules

- Touch ONLY: app.py, auth_routes.py, templates/interview_studio.html, static/js/interview-studio.js,
  tests/test_interview_studio.py, tests/test_auth.py, tests/test_search_visibility.py,
  docs/initiatives/PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001/**. NOT base.html, NOT
  dictation.js, NOT interview-studio.css (that's slice 3), NOT azure-pipelines.yml, NOT any SQL.
- Default-off flag; flag-off behavior must be byte-comparable for anonymous requests (add the test).
- Never weaken a failing test to pass; public-contract tests you must change get rewritten
  deliberately — keep a list of every test you rewrote and why, in the package docs folder.
- Run suites via `C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe` with
  `ANTHROPIC_API_KEY=test-placeholder-key` set. Node is not installed (one dictation test self-skips).

## Slice 1 — access boundary (all dark behind the flag)

1. **Flag**: add `PEERSLATE_INTERVIEW_STUDIO_AUTHENTICATED` to the config block (pattern:
   app.py:321-341, `os.environ.get(...) == 'true'`, default off, consumed with `is True`).
2. **HTML gates**: in `_render_interview_studio` (app.py:1841-1872), when the flag is on:
   ```python
   try:
       identity = get_current_identity()
   except AuthenticationRequired:
       return redirect(url_for("auth.sign_in", return_to=_safe_return_path(request.full_path.rstrip("?"))))
   except DatabaseServiceError:
       return _render_identity_storage_unavailable()
   ```
   (idiom: auth_routes.py:414-423; import what's needed the way auth_routes does; note
   `_safe_return_path` and `_render_identity_storage_unavailable` live in auth_routes — expose them
   cleanly, do not duplicate). Flag off → current behavior exactly.
3. **API gates**: at the TOP of the four live interview POST handlers (review :3598, improve :3712,
   nudge :3823, model-answer :3904), before body parsing, when the flag is on:
   AuthenticationRequired → `jsonify({"error": "sign_in_required"}), 401`;
   DatabaseServiceError → `jsonify({"error": "workspace_waking"}), 503` with `Retry-After: 5`.
   `/api/interview/coach` (:4093) stays 410 unauthenticated. Flag off → no identity work at all.
4. **Safe return**: auth_routes.py:83 `allowed = ("/app", "/the-slate")` →
   `("/app", "/the-slate", "/interview-studio")`. Extend tests/test_auth.py's hostile-shape matrix
   (:423-482) with the nine shapes for the new prefix plus `/interview-studiox`, `/interview-studio-x`;
   accepted: `/interview-studio`, `/interview-studio/history`, `/interview-studio?mode=video`.
5. **Headers**: in `prevent_stale_html` (app.py:919-987), mirror the Community rule (:926-931):
   when the flag is on, every `/interview-studio*` response gets hard-set
   `X-Robots-Tag: noindex, nofollow` and `Cache-Control: private, no-store`. Flag off → unchanged.
6. **Discovery**: remove `/interview-studio` from sitemap `public_paths` (:4243) and add
   `Disallow: /interview-studio` to robots.txt (:4222-4230) — UNCONDITIONALLY (correct in both
   worlds per architecture 04 §1). Fix tests/test_search_visibility.py accordingly if it pins these.
7. **Rate keys**: extend `_client_rate_limit_key` (:453-479) to return
   `'member:' + identity.user_key` when a request has an authenticated identity resolved
   (use the request-scoped `g.peerslate_identity`/principal marker; do NOT resolve identity inside
   the key function), IP fallback otherwise. Same budgets.
8. **Same-origin fail-closed**: in `_cross_site_refusal` (:432-450), when the flag is on AND the
   request carries a principal, a request with NEITHER `Sec-Fetch-Site` NOR `Origin` is refused 403.
   Anonymous/flag-off keeps current permissive behavior. Document this as a contract change in the
   package docs.
9. **Tests** (new class(es) in test_interview_studio.py + test_auth.py additions): signed-out GET
   302 + exact return round-trip; signed-out POST JSON 401 with no provider call (mock assert);
   malformed principal JSON 401 via existing app handler; DatabaseServiceError → 503 waking (HTML)
   and 503 JSON+Retry-After (API); headers on 200/302/401; sitemap/robots; member rate key;
   fail-closed same-origin; **flag-off byte-comparability**: with flag off, anonymous
   GET /interview-studio HTML equals the pre-change snapshot (assert on stable marker strings AND
   equality of the rendered body against a flag-off render captured in the same test run via config
   toggling — see Ask Pete's flag-off pattern in the test suites for the established approach).

## Slice 2 — storage isolation

1. **Scope injection**: in `_render_interview_studio`, when flag on, compute
   `storage_scope = 'member-' + hashlib.sha256(str(identity.user_key).encode()).hexdigest()[:20]`
   (exact `slate_board` precedent, app.py:1744-1746) and pass to the template; render as
   `data-storage-scope="..."` on the `[data-interview-studio]` root (template :16-32). Flag off →
   attribute absent.
2. **JS namespace**: interview-studio.js :36-42/:330-335 — when `data-storage-scope` is present,
   the storage prefix becomes `peerslate:interview-studio:<scope>:v3` (session/history/draft/probe
   keys). When absent (public page), keep the current v2 `<profileSlug>` prefix untouched. The
   legacy v1→v2 migration keeps running ONLY in the public branch. **No code path reads or writes
   the public v2/v1 keys when a scope is present** — no adoption, no deletion (owner decision Q-B).
   v3 records reuse the v2 record schema; the sanitizing read path (:1654-1772) is shared.
3. **API contract**: remove `profile_slug` from the four request payloads in JS (:1586-1593, :1913-1920,
   :2078-2086, :2509-2517). Server side, when flag on: ignore any client-supplied `profile_slug`
   (drop before use) and resolve the evidence/profile context from identity: Pete's account (matched
   via the existing `PEERSLATE_OWNER_USER_KEYS` mechanism / owner_authorization helper) → 'petec'
   fixture; any other account → empty evidence set (grounded/Compare will fail closed — slice 5
   completes the UX; here the server must already never leak the fixture to non-owner identities).
   Flag off: server behavior unchanged (slug still honored for the public page). Add the
   forged-slug test: identical response with and without a forged slug; non-owner identity never
   receives fixture evidence ids.
4. **Storage-failure truth**: JS — ensure `writeJSON` failures in `persistSession` and the three
   history mutators surface the existing truthful copy path rather than being silently dropped
   (minimal: reuse the draft-save failure pattern; full visual states come in slice 5).
5. **Tests**: two-identity isolation (distinct `data-storage-scope` values; 20-hex shape; no
   cross-render); scope absent flag-off; JS source assertions (v3 prefix construction, no v2 read
   in scoped mode, no `profile_slug` in payloads); log-safety: `user_key` never in interview log lines.

## Definition of done for this brief

Focused new tests green; FULL tests/test_interview_studio.py + tests/test_auth.py +
tests/test_search_visibility.py + tests/test_governance_pointers.py green; `git diff --check`
clean; a SLICE_NOTES.md in the package docs folder listing every changed public-contract test and
every behavior delta. Commit in small logical commits on the lane branch. Do not push.

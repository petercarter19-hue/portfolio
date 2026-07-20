# 03 — Integrating the keepers against the RELEASED Studio

This file describes how the KEEP verdicts in `02_…` would attach to the
Interview Studio that is live today, not to the Studio the old branch was
written against. Nothing here has been built.

## What is actually on `main` right now

Verified by reading the files on `origin/main` at
`531013dd8c1a05e2443becd881a226755f27ca14`.

### Routes

| Route | File | Auth | Notes |
|---|---|---|---|
| `GET /interview-studio` | `app.py` `interview_studio()` | **None — fully public** | Renders `_render_interview_studio('me')` |
| `GET /interview-studio/history` | `app.py` `interview_studio_history()` | **None — fully public** | Same template, `data-is-panel="history"`; history is browser-local |
| `POST /api/interview/review` | `app.py` | None | Written-practice scoring |
| `POST /api/interview/improve` | `app.py` | None | Coaching |
| `POST /api/interview/model-answer` | `app.py`, `@limiter.limit('6 per minute')` | None | Grounded model answer |
| `GET/POST /app/...` | `owner_routes.py` (`owner` blueprint) | `get_current_identity()` | All private member surfaces live here |
| `GET /api/v1/owner/home` | `owner_routes.py` | Authenticated, flag-gated | Returns neutral `404` while `PEERSLATE_OWNER_HOME_ENABLED` is false |

**There is no `/api/interview` blueprint on `main`.** The old branch's
`interview_story_api.py` would be an entirely new module, and its
`url_prefix="/api/interview"` would sit alongside three existing `app.py` routes
under the same path prefix. That mixing of a blueprint and bare `app.route`
handlers under one prefix works in Flask but is worth avoiding; see "Route
placement" below.

### The released grounding path

`interview_model_answer()` on `main`:

1. Gates on `get_interview_entitlements()['model_answers']` (currently always `True`).
2. Requires JSON, rejects cross-site `Sec-Fetch-Site` and mismatched `Origin`.
3. Reads `mode` from the body, **defaulting anything unrecognized to `member_history`**.
4. Builds evidence from `_interview_page_context(profile_slug)` →
   `_interview_evidence_from_profile()` → up to ten metrics from
   `static/data/resume_data.json`. **All public fixture data.**
5. Calls `claude-haiku-4-5-20251001`, validates the JSON against the evidence
   map, and signs a follow-up context containing
   `profile_slug`, `question`, `level`, `family`, `answer`, `evidence_ids` —
   with **no owner binding**.

### The released client contract

`static/js/interview-studio.js` posts to `/api/interview/model-answer` with
`profile_slug`, `question`, `follow_up`, `context_token`, `level`, `family`, and
a lowercase `mode` that is `'member_history'` for follow-ups and
`selectedAiMode()` otherwise. `selectedAiMode()` reads the checked radio in
`[data-is-ai-mode-group]` and falls back to `'member_history'`.

The template's three radios are `best_practice`, `member_history`, `compare`,
with `member_history` checked by default and labelled
"Use {first_name}'s **public** history."

## Integration shape

### Principle: add a fourth source, do not repurpose the third

The released `member_history` mode means *public fixture history* and says so on
screen. A private-history capability must be a **new, clearly distinct source**,
not a redefinition of the existing one. Redefining it would silently change what
a live, publicly-labelled control does — which is precisely the failure mode the
Owner Visual Integrity Standard exists to prevent.

Proposed mapping, offered for review:

| Released `mode` | Proposed `source_mode` | Meaning |
|---|---|---|
| `best_practice` | `ILLUSTRATIVE` | Generic example, no personal history |
| `member_history` | `PUBLIC_PROFILE` | Approved **public** résumé evidence — unchanged behavior, honest name |
| `compare` | `COMPARE_ILLUSTRATIVE` | Both of the above, stacked — unchanged behavior |
| *(new)* | `PRIVATE_HISTORY` | Confirmed, AI-permitted, private member stories |
| *(new)* | `COMPARE_PRIVATE` | Private history alongside an illustrative example |

This differs from the old branch, which had only three modes and quietly
redefined `MEMBER_HISTORY` from public to private. That redefinition is the
single riskiest thing in the branch and should not survive.

### Backward-compatible sequencing

The released client is live and cached. A migration that breaks it is a
regression.

1. **Phase A — accept both.** The route accepts the legacy lowercase `mode` and
   the new uppercase `source_mode`. Legacy values map to the table above.
   `source_mode` wins when both are present. Nothing in the client changes.
2. **Phase B — fail closed for new modes only.** A *missing* mode continues to
   mean `PUBLIC_PROFILE` for legacy callers, but any `PRIVATE_*` mode must be
   stated explicitly and can never be reached by default or by coercion. This
   preserves K-7's actual safety property — no private read by accident —
   without a breaking change.
3. **Phase C — client migration.** The Studio starts sending `source_mode`
   explicitly. Only after that is live may the legacy fallback be removed, and
   only through its own package.

### Route placement — two options

**Option 1: private story API under `/app`.** New authenticated blueprint at
`/app/api/interview/stories` (or extend the existing `owner` blueprint in
`owner_routes.py`). All create/confirm/permission/archive/delete traffic lives
with every other private surface. The public Studio calls only the public
model-answer route, which reads private stories server-side after resolving
identity itself.

*Pros:* one auth boundary, matches Capture/Moment/Voice/Photo/Home precedent,
no new public-prefix surface. *Cons:* the Studio page would be issuing
cross-prefix calls.

**Option 2: separate authenticated blueprint at `/api/interview/stories`.**
Closest to the old branch. Keeps interview concerns together.

*Cons:* puts an authenticated blueprint under a prefix currently owned by three
unauthenticated `app.py` routes, and creates a second private-data entry point
outside `/app`.

**This proposal leans to Option 1** on precedent grounds, but flags it as
question 3 in `06_…`.

### Where the private read would attach

Inside `interview_model_answer()`, only when `source_mode` is a `PRIVATE_*`
value:

```
resolve source_mode (explicit, fail closed)
  └─ PRIVATE_*?
       ├─ get_current_identity()  →  AuthenticationRequired?
       │     └─ return the PERMISSION_REQUIRED sufficiency payload (see C-3)
       ├─ story_ids supplied?
       │     ├─ yes → resolve_sources(user_key, story_ids)   [K-3]
       │     └─ no  → match() → evaluate()                    [K-5]
       │                 └─ SUFFICIENT? auto-select : return sufficiency payload
       ├─ build prompt from <member_story_data> blocks         [K-6]
       ├─ call the model, validate against the resolved source map
       ├─ record_answer(server-resolved source set)            [K-4, corrected per D-5]
       └─ sign context with owner_user_key + source_mode        [K-9]
```

Everything above the `PRIVATE_*` branch is untouched, so the public path keeps
its exact released behavior.

### Reusing released infrastructure rather than rebuilding it

| Need | Released thing to reuse | Do not build |
|---|---|---|
| Identity | `identity.get_current_identity()` / `get_optional_identity()` | Any new identity resolution |
| Procedure access | `services.database_service` allowlist + `DatabaseServiceError` | Direct SQL from a service |
| Voice input for stories | PS-VOICE-001 private Voice Capture | A second `SpeechRecognition` path |
| Canonical private records | PS-MOMENT-001 `moments` / `moment_versions` | A duplicate canonical record — see C-1 |
| Exact-version references | PS-PLACEMENT-001 contract and procedures | A parallel reference model |
| Migration tooling | `scripts/apply_sql_migrations.py` `APPROVED_OPTIONAL_MIGRATIONS` | Additions to `MIGRATION_FILENAMES` |
| Owner API shape | `owner_routes.py` patterns (JSON contract, neutral 404, flag gating) | A novel API convention |

### Feature flag

Every recent private package shipped dark. `PS-CAPTURE-MEDIA-001` released with
`CAPTURE_PHOTO_ENABLED=false`; `PS-HOME-BACKEND-001` released with
`PEERSLATE_OWNER_HOME_ENABLED=false` and a neutral `404` on the API.

Any private-history work should follow the same pattern: an environment flag
defaulting to off, a neutral `404` (not a `403`) on the private endpoints while
off, and no change whatsoever to the public Studio's rendered output until an
explicit, separate enablement decision.

### UI work is a separate, later package

The keepers are all backend. The member-facing experience — a story-capture
dialog, a sufficiency state in the answer workspace, candidate selection, a
fact-boundary strip, a permission toggle — must be designed fresh against the
released 5A-light/5C-dark component language, produced as production-intent
demonstrations, and accepted by Pete and a designated manager under the Owner
Visual Integrity Standard before implementation. The old branch's markup is
reference material for *what states are needed*, not for how they look.

### Homepage parity

`CURRENT_BASELINE.yaml` records the cross-product projection rule: a material
user-facing product change requires a same-wave homepage parity update or an
exact downstream parity package. Interview Studio is a named current example,
and `PS-HOME-INTERVIEW-PARITY-001` is already active with parity open.

A backend-only, flag-off private-history release changes nothing a visitor
sees, so it would carry a homepage-impact assessment concluding "no parity
change required while the flag is off." Any later *enablement* would trigger a
real parity obligation and must not be blended into the parity lane that is
already in flight.

## Test surface this would need

Re-derived against what exists on `main`, following the shape of
`tests/test_moment_migration.py`, `tests/test_placement_migration.py`, and
`tests/test_owner_capture.py`.

- Migration file tests: forward/rollback/verifier exist; transactional; declares
  its prerequisites; registers in the ledger; refuses rollback when member rows
  exist.
- `services/database_service.py` allowlist tests for each new procedure name.
- Service tests against a fake database for: sufficiency classification and every
  reason code; the exact-set match failure in `resolve_sources`; UUID rejection;
  bounded-text rejection; the "missing visibility is unsafe" rule.
- Route tests: explicit source mode required for `PRIVATE_*`; legacy `mode`
  still works; anonymous `PRIVATE_*` returns the agreed gate state; a follow-up
  token minted for owner A rejected for owner B; flag-off returns neutral `404`.
- Two-owner isolation tests at both the service and SQL levels — see `05_…`.
- Both guardrail suites (`tests/test_site_rules.py`,
  `tests/test_governance_pointers.py`) and the full suite.

Local command, per `NEXT_TASK_BOARD.md`:

```bash
venv/bin/python -m unittest discover -s tests -t .
```

`pytest` is not installed in the primary Mac venv and silently does nothing.

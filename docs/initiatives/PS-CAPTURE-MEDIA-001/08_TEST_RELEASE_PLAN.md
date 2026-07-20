# PS-CAPTURE-MEDIA-001 - Test and Release Evidence Plan

## Focused application tests

- Auth redirect and same-origin write rejection for every photo endpoint.
- JPEG/PNG happy paths; empty, oversized, mislabeled, truncated, animated,
  unsupported, polyglot-like, excessive-pixel, and excessive-dimension denial.
- Source-key/blob-name generation, no overwrite, no original filename/metadata,
  byte/digest verification, and safe error/log behavior.
- Scan pending/clean/malicious/error/not-scanned/timeout/cap/unavailable states,
  repeated reconciliation, and fail-closed retrieval/confirmation.
- Pillow allowlist, decompression-bomb warning-as-error, full pixel load,
  orientation, derivative bounds, deterministic metadata removal, and resource
  cleanup on exceptions.
- Owner review, note validation, idempotent/concurrent confirm, stale token,
  correction, archive/restore, schema-v3 export, original download, and
  derivative preview headers.
- Draft and confirmed deletion across both Blobs, partial failure/retry,
  provider-remediated absence, body-free tombstone, and existing Moment source-
  deleted behavior.
- Feature flag off, text fallback, Voice regression, and neutral errors.

## SQL tests

- Static migration/dependency/ledger/fingerprint checks.
- Real SQL Server apply, verify, normal guarded rollback, reapply, and reverify
  in an isolated database.
- Two synthetic owners proving no source, state, dimensions, scan status, Blob
  locator, preview, download, link, Capture, export, or deletion leakage.
- State-machine constraints, payload-live/deleted checks, composite ownership,
  one source/one Capture uniqueness, exact link, row-version concurrency, and
  deterministic duplicate confirmation.
- Shared Capture procedures preserve existing text/Voice result shapes and
  Moment/Placement behavior.
- Rollback refuses with data, later migration/dependency, or protected-procedure
  drift and leaves all existing foundations intact.

## Infrastructure and provider proof

Use only a disposable isolated account/container and synthetic nonpersonal
fixtures before production:

- plan mode proves no mutation;
- secure-transfer/TLS/public-access/shared-key/GPv2/container privacy;
- exact App Service test identity roles and no broad Blob Data Owner/tag-write;
- Defender on-upload enabled, scan cap/remediation configured, and scan results
  observable;
- clean JPEG/PNG scan to safe derivative;
- sanctioned harmless malware-detection test only in the disposable account,
  proving no application delivery and provider remediation;
- scan error/not-scanned and cap-fail-closed simulation;
- managed-identity upload/tag-read/download/delete and final absence; and
- exact disposable resource deletion with existence false.

Do not use production member files, retrieve settings/keys, or print resource
provider payloads containing sensitive values.

## Security and data-rights tests

- Guessed/cross-owner keys across GET/POST, stale tokens, redirects, timing,
  concurrent save/delete, preview/original, export, and retry.
- No public URL/SAS/credential/client path in HTML, JSON, redirects, logs,
  audit, database text, Blob name, or metadata.
- Original EXIF/GPS fixture remains only in the clean private original; safe
  derivative and SQL/log/export metadata contain no EXIF/GPS values.
- Authorized original export returns exact bytes only to the owner with
  no-store/nosniff/generic filename.
- Explicit deletion proves both Blob absences before SQL content clearing and
  success; archive proves retention.
- Unsafe input cannot be previewed/exported/confirmed by either owner.

## Accessibility and visual evidence

Capture named comparison evidence against the authority in
`06_EXPERIENCE_ACCESSIBILITY.md`:

- desktop opening, selection, scanning, review, confirmed list, and deletion;
- mobile portrait opening/camera choice, scanning, review with keyboard, and
  persistent save;
- unsupported/unsafe/scan error/storage unavailable/stale/deletion retry;
- keyboard-only complete path and visible focus;
- screen-reader names/order/live regions/status;
- native browser 200% zoom/reflow proof;
- reduced-motion proof;
- long note/long error/no-JavaScript/text fallback; and
- a parity/deviation matrix with every deviation resolved or explicitly
  accepted by Pete and the designated manager.

## Repository regression gates

- New photo-focused tests.
- Existing Capture, Voice, Moment, Placement, owner route, database, migration,
  identity, site rules, and governance tests.
- Complete configured `python -m unittest discover -s tests -q` suite.
- Changed Python compilation/import check.
- `git diff --check` and complete-diff review against exact base.
- Changed-file reservation allowlist and secret/credential scan.
- Dependency install/build proof on the same Linux pipeline class as production.

## Production release evidence

After accepted PRs and deploy only:

1. Exact Azure PR, squash SHA, Build and Deploy run IDs for backend,
   experience, homepage parity, and closeout.
2. Production control-plane verification of new private account, container,
   Defender/cap/remediation, and exact roles without reading settings/secrets.
3. Canonical `/`, `/app/capture`, auth redirect, CSS/JS signatures, and no
   unexpected public media route.
4. Signed-in synthetic owner lifecycle: supported photo -> scan -> derivative
   -> note -> explicit save -> correction -> archive/restore -> JSON/original
   export -> delete -> both Blobs absent -> text/Voice still usable.
5. Second-owner denial using synthetic test accounts only.
6. Production desktop/mobile screenshots accepted by Pete and manager.
7. Homepage projection truth/parity accepted and live.

If a signed-in production test cannot be completed safely, report that exact
boundary. Asset/auth checks alone do not prove the full lifecycle.

## Pass standard

The writer returns `Pass` only when every required automated, isolated real-
resource, security, data-rights, visual, and regression gate passes with no
unaccepted material deviation. `Conditional` names the exact missing evidence
and keeps release/flag off. `Fail` blocks the package.

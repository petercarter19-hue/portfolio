# PS-AUTH-CALLBACK-001 — Entra callback hardening

## Authority and ownership

- Owner authorization: Pete Carter, 2026-07-23, “do everything please,” in
  response to the reproduced production sign-in failure.
- Manager and sole writer: the current Codex session.
- Authoritative base:
  `e2c084c8d701936684cd9267d672dbb439bba62d` from Azure DevOps
  `origin/main`.
- Working branch: `work/2026-07-23-auth-callback-hardening-001`.
- Writable scope:
  - the callback hardening script and its tests;
  - the shared template reference required to run it before page scripts;
  - this package’s evidence and completion report.
- Forbidden scope: identity-provider provisioning, secrets, database schema,
  shared governance pointers, homepage design, and unrelated active lanes.

## Verified production symptom

The Microsoft Entra External ID sign-in completed, but the browser returned to
`/app` with an opaque Easy Auth callback value in the URL fragment while the
old “Sign in is not configured yet” document remained visible. Navigating the
same authenticated browser to a clean `/app` immediately rendered the private
owner workspace with the signed-in member.

This evidence separates two facts:

1. Easy Auth, the trusted identity header, and the database account mapping are
   operational.
2. The browser callback transition can preserve stale pre-sign-in document
   content because a fragment-only URL change is not sent to Flask and does not
   require a new document request.

The callback value appeared in user-provided evidence. It is treated as
exposed session material: it must not be copied, decoded, logged, persisted, or
used as application identity.

## Approved implementation

Load a small dependency-free script at the start of the shared document head.
It recognizes only the `#token=` prefix, never reads the value, removes the
entire fragment with `history.replaceState`, and reloads the same path and
query. The resulting network request lets App Service Easy Auth attach its
trusted server-side identity headers.

The script checks three browser lifecycle points:

- initial execution;
- `hashchange`, for an in-place fragment callback;
- `pageshow`, for a document restored from the back/forward cache.

An unrelated fragment is left untouched. If the History API is unavailable,
the browser replaces the current entry with the clean URL.

## Acceptance

- A callback fragment is removed without being parsed or persisted.
- The clean route is requested exactly once.
- In-place and back/forward-cache callback returns are covered.
- Ordinary PeerSlate fragments are unchanged.
- Existing server-directed login, safe return-path validation, trusted-header
  identity mapping, and sign-out protections remain green.
- Azure DevOps build, squash merge, deployment, and a fresh production sign-in
  are recorded in the package completion report before this work is called
  live.

# PS-LEGACY-PROJECTS-RUNTIME-RETIREMENT-001

## Outcome

Complete Phase B of the accepted legacy Projects privacy containment. Remove
the dead browser-facing Projects Board loader and its inert tombstone file,
then make the retired static address return `410 Gone` without content for
GET, HEAD, query, conditional, and Range requests.

This is a **Protected**, repository-only containment package. Repository
authority is through an accepted merge; production authority is withheld.
The full `PS-PROJECTS-001` product and Profile Projects projection remain
planned for Audit Round Two and are not activated by this work.

## Included work

- remove `PROJECT_BOARD_FILES`, `_load_project_board`, and
  `_normalize_board_project` from `app.py`;
- delete `static/data/projects_board.json` from the current tree;
- register one exact GET/HEAD route for the retired static address that returns
  an empty `410 Gone` response with `no-store` and `nosniff` headers;
- replace Phase A tombstone-response tests with exact absence and retirement
  tests; and
- preserve the existing Projects/Work redirects, distinct résumé case-study
  records, search exclusion, sitemap exclusion, and unrelated site behavior.

## Deferred Package Registry sequence

`PS-OPPORTUNITY-SLATE-003` owned `docs/governance/PACKAGE_REGISTRY.json` when
this package activated. The registry is therefore excluded from the initial
claim. This implementation must not merge until that owner closes, a governed
`extend-surfaces` transition adds the registry, the package is registered, the
branch refreshes from current `origin/main`, and all validation plus a fresh
independent exact-SHA review pass.

## Explicit exclusions

No Projects workspace, Profile Projects destination, Project schema, visual
direction, navigation, shared shell, résumé case-study deletion, image
removal, deployment, production mutation, GitHub mirror change, cache/CDN
operation, search-provider operation, history rewrite, grant, identity,
provider, configuration, or other external action is authorized.

## Acceptance

- the legacy static file and all dead loader symbols are absent;
- the exact retired address returns `410` and zero response bytes for GET,
  HEAD, query, conditional, and Range variants;
- the response sets `Cache-Control: no-store, max-age=0`, sets
  `X-Content-Type-Options: nosniff`, and emits no ETag, Content-Range, or
  cookie;
- current Projects/Work aliases still redirect directly to résumé experience;
- résumé case studies remain separate and unchanged;
- search and sitemap still omit the retired board;
- focused and full repository tests, secret scans, registry checks, delivery
  preflight, and `git diff --check` pass; and
- a fresh independent reviewer accepts one immutable exact candidate SHA.

## Truthful release state

A repository merge does not retire the endpoint in production. The current
public response and any stale cache remain unchanged until a separately
authorized exact-main deployment and public host/cache verification occur.

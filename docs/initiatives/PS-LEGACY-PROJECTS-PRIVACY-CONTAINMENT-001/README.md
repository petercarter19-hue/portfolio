# PS-LEGACY-PROJECTS-PRIVACY-CONTAINMENT-001

## Outcome

Contain the confirmed anonymous disclosure of the retired browser-facing
Projects Board payload at the repository layer. The tracked static JSON file is
replaced by one inert empty tombstone:

```json
{
  "retired": true,
  "projects": []
}
```

The original payload is not copied to another current-tree path. Existing Git
history remains intact.

## Classification and boundary

The disclosed file is classified as an unverified personal-looking legacy
fixture with explicit private labels. This package does not call it verified
member data, safely synthetic data, or a legal breach. It is a confirmed
anonymous disclosure/control defect on a Protected path.

This Phase A package is repository containment only. The static endpoint still
returns `200 application/json`, but its body contains no project records.
Runtime removal and a `410 Gone` response belong to the later
`PS-LEGACY-PROJECTS-RUNTIME-RETIREMENT-001` package after `app.py` is available.

## Included work

- replace `static/data/projects_board.json` with the exact tombstone;
- replace tests that preserved the six retired records with exact GET, HEAD,
  query, conditional, Range, search, sitemap, redirect, and résumé case-study
  regression coverage;
- correct two current-state statements in the planned Projects direction;
- record Protected independent exact-SHA review and repository close evidence;
  and
- register this package after the current Package Registry owner releases that
  shared file.

## Explicit exclusions

No `app.py` or dead-loader removal, Profile Projects work, image removal,
navigation change, deployment, production mutation, GitHub mirror operation,
cache/CDN purge, search-provider removal, history rewrite, schema, identity, or
other external action is authorized or performed.

## Acceptance

- current-tree JSON bytes equal the exact tombstone and its parsed keys are
  only `retired` and `projects`;
- the old payload digest does not match any current-tree or candidate-artifact
  file and known private markers are absent from the candidate artifact;
- anonymous GET, HEAD, query, conditional, and Range behavior can expose only
  tombstone bytes;
- retired aliases still redirect directly to résumé experience, distinct
  résumé case-study behavior is unchanged, and search/sitemap do not advertise
  the retired board;
- current-tree and full-history secret scans pass; the full-history scan does
  not rewrite or remove history;
- registry, delivery preflight, focused and full CI checks pass; and
- a fresh independent reviewer accepts one immutable exact candidate SHA.

## Truthful release state

Repository merge is not production containment. Until a separately authorized
exact-main deployment is completed and every public host plus stale-cache
behavior is verified, the already-deployed legacy response may remain
available. The stale public GitHub mirror is also outside this package and
requires its own authorized operation.

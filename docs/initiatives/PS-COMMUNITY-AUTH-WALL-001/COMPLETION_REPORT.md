# PS-COMMUNITY-AUTH-WALL-001 — completion report

**Outcome:** COMPLETE AND LIVE, 2026-08-09. PeerSlate Community now requires trusted
authentication on every HTML, JSON, search, Voice, attachment, and media path. The
anonymous public experience and every demo/fixture fallback are retired in all flag states.

**Delivery path:** Protected · **Writer:** Claude Fable 5 session · **Owner:** Pete Carter

## Owner authority

- Direction, 2026-08-08: *"Let's just position this firmly behind the sign in wall. That
  will make life easier for all of us. We can make a demo down the road. Not a working
  demo, but maybe a video or something else when it is time to get this out to the audience."*
- Execution, 2026-08-08: *"You can execut everything tonight to live deployment"*, reaffirmed
  *"Okay. Let's get going."*
- Retention decision v1.0 approved as drafted, 2026-08-08 (durations unchanged,
  authenticated-audience language). Recorded in `RETENTION_DECISION_v1.0.md`.
- Production checkpoint for run 711 approved by Pete at the gate.

## Identity of the change

| | |
|---|---|
| Activation | PR 357 → main `0ee01b9df18e6a858d5fe49a6584bfd0854defda` |
| Base | `eb5f5ddd8ea0a99c639833dbde3d571938b23645`, rebased to `0ee01b9`, then `f1cab65` |
| Candidate reviewed | `d75ac0b18a690d26c61cb29dcea82b359281151d` |
| Merge | Azure PR 361, squash → main `7a7c99de085a8d25ab12ce386c7cb2509cda2057` |
| Deploy | Pipeline run 711 (batchedCI, `forceProductionDeploy=false`, `schemaAction=none`) |
| Live release | `/healthz` = `e1a3b800aec6444f1a35c80a` = derived identity of (`7a7c99d`, 711) |

## Changed surfaces

`app.py`, `auth_routes.py`, `community_api.py`, `community_routes.py`,
`templates/community_feed.html`, `templates/community_policy.html` (new),
`templates/base.html`, `templates/partials/homepage/_voice_hero.html`,
`static/js/community-v1.js`; deleted `services/community_demo_feed.py`,
`scripts/preview_community_public_demo.py`, `scripts/verify_community_public_demo_browser.py`;
package docs; and the test files listed under recorded scope in `README.md`.
33 files, +1819 / −1726.

## Verification

- **Full repository suite: 3274 passed, 4 skipped, 0 failed, 4257 subtests passed.**
- **Two independent fresh-context adversarial reviews, both no-blocker.** Each ran live
  probes (not code reading alone): a 24- and a 47-input battery against the widened
  return-path allowlist, signed-out sweeps of every route in both flag states with services
  patched and `assert_not_called` asserted, invalid/unmappable principal and identity-DB
  failure injection, and a full owner/non-owner mutation matrix. Both independently
  reported the same single non-blocking nit (HTML 503 vs API 401 for an unmappable
  principal); it is pre-existing app-wide behavior and was deliberately left out of scope.
- **Live anonymous production sweep** before and after: `LIVE_EVIDENCE_BEFORE.md`,
  `LIVE_EVIDENCE_AFTER.md`. Before: `/the-slate` and the Community API returned 200 to
  anyone, with `demo_mode: true` fabricated content. After: sign-in redirects with exact
  return paths, 401 on every API and both attachment endpoints, 404 or redirect on retired
  surfaces, `Disallow: /the-slate`, zero Community paths in the sitemap, zero demo markers.
- **Governance guards:** 146 passed at closeout, including the baseline word cap, the
  active-lane mirror, and release-truth lockstep against the new SHA/pipeline/release.

## Release state

Merged, deployed, and verified live. This is a runtime release, not a documentation-only
change; the closeout record itself merges with `[skip ci]`.

## Honest limitations

1. Content public before this release may persist in screenshots, downloads, caches, or
   third-party copies. The wall cannot retract those; the approved retention decision and
   the member policy page both say so plainly.
2. The stored audience token remains the transitional literal `public`. Enforcement is in
   the application layer; the schema migration is a later Protected package.
3. Attachment delivery authorizes any authenticated member, with published-state filtering
   inside the SQL procedure. Unchanged by this package — it tightened from anonymous to
   members-only — and recorded here rather than introduced.
4. An unmappable principal yields 503 on HTML and 401 on the API. Both fail closed and
   never render anonymously; the inconsistency is app-wide and out of scope.
5. Retired templates and `people_interests_api.py` remain on disk, unrouted, per the
   repository's rollback convention. They are dead code, not live surfaces.
6. Rollback truth: the pre-wall build is **not** a safe rollback now that authenticated
   Community exists — flag-on there means anonymous reads. Safe stop is availability off
   (neutral 404) with data preserved, then roll forward.

## Next action

Lane moves to closing; surfaces and the lane slot are released. The freed slot is intended
for PS-AGENT-OPERATIONS-001 (split routine web deploy from gated schema operations), whose
design handoff is at `iCloud Drive/Claude/HANDOFF-PS-AGENT-OPERATIONS-001-DESIGN-2026-08-09.md`.
Worktree and branch disposal follow `BRANCH_DISPOSITION_RECORD` after this closeout merges.

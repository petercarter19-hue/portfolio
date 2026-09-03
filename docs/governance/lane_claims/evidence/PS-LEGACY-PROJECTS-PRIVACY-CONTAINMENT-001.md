# PS-LEGACY-PROJECTS-PRIVACY-CONTAINMENT-001 — candidate evidence

## Scope and authority

Pete selected this Phase A repository containment under reference
`session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`.
Repository authority is through merge; production authority is withheld. This
package performs no deployment, live change, GitHub mirror operation, cache or
search-provider purge, history rewrite, schema, identity, or other external
operation.

## Candidate outcome

Exact candidate `5544d76e508b4066b001a12f6867334bc5c34cc2` replaces the
retired browser-facing Projects Board payload with the exact 40-byte inert JSON
tombstone containing `retired: true` and an empty `projects` array. It removes
tests that preserved the six retired records and adds exact anonymous GET,
HEAD, query, ETag conditional, and Range response proof. Retired Project aliases
still redirect directly to résumé experience; separate résumé case studies are
unchanged; search and sitemap do not advertise the retired board.

Only two current-state Projects direction passages are corrected. The package
is registered once under `current_protect`, with reconciled counts of 69 in
that category and 137 total. `app.py`, dead loader code, Profile Projects,
navigation, images, and all live surfaces remain outside this Phase A package.

## Validation

- Full repository regression: 5,513 passed, 26 inherited skips.
- Focused package-registry, Projects, navigation, and search regression: 49
  passed; Projects-only response and boundary suite: 13 passed.
- Exact tombstone size: 40 bytes; SHA-256
  `eef59c8b0f0992137e83eb33be49047ea4b4a2b7e673226eb6709b103a2d3536`.
- Current-tree secret scan: 37,330,671 bytes, zero findings.
- Full-history secret scan: 2,435 commits / 93,787,024 bytes, zero findings.
- Every current-tree file and every file in a 3,619-file candidate archive was
  checked: no file matches retired-payload SHA-256
  `f3e2e933146005ccb6879737cbc78b691b3411c5fbdbee5d7fbc2796c914b642`,
  and six unique title/slug markers for its three private-labelled records are
  absent. The candidate archive SHA-256 is
  `eb2b3afdcf4969ecf1bd0c8b88dc2b0bca68637bf84779b1f204045678715dd7`.
- Repository evidence policy, SQL migration registry consistency, runtime and
  operational-script compile, `git diff --check`, and exact write preflight:
  pass.
- Changed paths are exactly the ten claim surfaces after excluding the claim
  itself and including this fixed evidence file and receipt.

## Governance sequence and independent review

Claim-only activation PR 868 / build 2307 merged at
`50e983fbacd06d172307be4f78fb57e8fbefa07a`. Pre-registry candidate
`860df6e4bc302ed32b872ee9cff95262c5d0e9dc` received PROVISIONAL ACCEPT at
`2026-09-03T01:16:32Z` from
`agent:/root/profile_critical_path_prep`, with no implementation finding and
the declared registry blocker preserved.

After Owner Home closed and released the registry, independently passed exact
claim-only control commit `da2cacf50a2a8321ba2574149088da8e08befadc`
added only `docs/governance/PACKAGE_REGISTRY.json` to this claim. PR 871 / build
2314 merged that extension at
`fb6316dfd8a857c7da8f10717761b96f26b766ef`. The implementation branch then
refreshed from that exact main and added only the authoritative registry entry
and counts.

A fresh independent exact-SHA and delta review ACCEPTed final candidate
`5544d76e508b4066b001a12f6867334bc5c34cc2` with no blockers. Reviewer:
`agent:/root/owner_home_retirement`; reviewed at
`2026-09-03T02:01:34Z`. The reviewer confirmed the complete claim scope,
tombstone bytes and semantics, anonymous HTTP boundary, redirect and résumé
separation, search/sitemap exclusion, marker/digest and artifact proof,
registry integrity, full tests, secret scans, preflight, current main, and
collision state. This acceptance authorizes repository merge only.

## Honest limitations

This is repository payload containment, not endpoint retirement and not a live
fix. Git history remains intact. The public GitHub mirror and deployed hosts
are separate. A future separately authorized exact-main deployment must prove
the public host matrix and stale-ETag behavior. A later, separately claimed
Phase B may remove the dead loader and return `410 Gone` after `app.py` is
available.

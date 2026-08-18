# Fresh corrected-candidate review handoff

## Assignment

Perform a fresh read-only independent review of the corrected Community
authoring candidate. The prior exact candidate passed its four reconciliation
questions but was rejected for a newly reproduced create-draft deletion path.
Do not edit the branch, merge it, deploy it, enable configuration, or describe
it as live. Return one verdict: **ACCEPT** or **REJECT with actionable
findings**.

## Exact review target

- Repository: PeerSlate `portfolio-site`
- Branch: `work/2026-08-17-community-authoring-runtime-001-r2`
- Original product base: `ec65f4c3341056978d73534d74e5555e030f3c12`
- Current merge-control base: `ffbeca40868e4aee414b68bf48a486d833d1a0e3`
- Frozen implementation-content SHA:
  `887bd087e722562fd4c78f4d75a3b128d1cd74d9`
- Product diff:
  `ffbeca40868e4aee414b68bf48a486d833d1a0e3..887bd087e722562fd4c78f4d75a3b128d1cd74d9`
- The branch head after the implementation SHA adds only updated package
  documentation. Pete/Codex will provide that pushed head SHA when the handoff
  is initiated.
- Superseded rejected implementation-content SHAs:
  `6e3936f89c28edb2e34ecf35fd1ceb33c1b74e91` and
  `04c3dff5985bb4c07350a2c3c669602addf192a0`; incomplete correction SHA
  `4dc1cba43bb3dedc602a3affd0061f359610299d` was also rejected.

## Read first

1. `README.md`
2. `REVIEW_RECONCILIATION.md`
3. `00_ARCHITECTURE.md`
4. `OWNER_TECHNICAL_COMPLETION_REPORT.md`
5. `../PS-COMMUNITY-VISUAL-REFINEMENT-001/03_IMPLEMENTATION_HANDOFF.md`
6. `../PS-COMMUNITY-VISUAL-REFINEMENT-001/02_VISUAL_AUTHORITY_MANIFEST.md`
7. The ten files under the manifest's Pete lock.

The current color direction was accepted for this implementation even though
Pete considers it green-heavy. A later whole-site color review is deliberately
deferred; do not reject this candidate merely for not performing that broader
redesign. Do reject a material mismatch to the locked semantic color roles or
the compact white composer.

## Required review questions

1. Are the two visually hidden native selects excluded from sequential
   keyboard order while remaining enabled, named submission controls?
2. Is the Community publication confirmation compact and centered at phone
   widths and short 200%-reflow viewports, without inheriting the full-height
   composer treatment?
3. Do Active Questions and My Mix now render truthful empty states rather than
   hard-coded member activity or recommendations?
4. Are long restored drafts and long edited posts measured only after the
   composer opens, immediately visible, bounded, and internally scrollable?
5. Does the desktop composition retain Mine / Ours / Beyond with Ours dominant
   and avoid the superseded blue-card/full-width-media treatment?
6. Is the composer compact and efficient across desktop, iPad, phone, 320px,
   large text, and 200% reflow, with no fixed oversized writing box?
7. Does the audience popover overlay without resizing the composer, keep only
   Community enabled, close with Escape, and restore focus?
8. Are Photo, Video, File, Voice, and AI icon-only controls meaningfully named
   and colored blue, coral, amber, teal, and violet, with unavailable tools
   represented truthfully?
9. Do signed-in identity, owner-only authoring, draft privacy, attachment
   authorization, deliberate Community publication, private saves, replies,
   and failure states remain fail-closed?
10. Does AI remain an unavailable optional proposal surface with no provider
   call, silent replacement, save, or publication?
11. Are published attachments compact and are no more than three reply/update
   previews shown before the exact View all continuation?
12. Do keyboard focus, accessible names, touch targets, forced-colors CSS,
   reduced motion, and no-horizontal-clipping contracts remain intact?
13. Does `PACKAGE_REGISTRY.json` add only the two Community packages exactly
   once in `current_protect`, with counts `61` and `119`?
14. Is every implementation change inside the active lane's authorized
    surfaces, with no schema, application registration, deployment, feature
    enablement, or production-data change?
15. After a create draft is saved locally, does successfully editing an
    existing post leave that draft and its pending create-command key intact,
    while a successful new post leaves its consumed draft/key absent even
    after the asynchronous composer `close` event?

Do not reopen the claimed 901-1288px rail-disappearance finding without new
contrary evidence. The later equal-specificity `.cv1-rail { display: block; }`
rule overrides the earlier media-query hide declaration. No breakpoint change
was implemented, and browser verification found both rails visible at 901,
1024, and 1180px.

## Reproduction

Use a clean detached checkout of the pushed branch. The local closed preview
is fixture-only and never touches persistence:

```bash
PEERSLATE_PRIMARY_FEED_PREVIEW_PORT=5055 \
  /tmp/peerslate-community-venv-20260817/bin/python \
  scripts/preview_community_primary_feed.py
```

Focused verification:

```bash
/Users/petercarter/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  --check static/js/community-v1.js

/tmp/peerslate-community-venv-20260817/bin/python -m unittest \
  tests.test_community_authoring_runtime \
  tests.test_community_public_pilot \
  tests.test_community_secondary_states \
  tests.test_community_voice \
  tests.test_community_draft_expiry \
  tests.test_community_tabs \
  tests.test_package_registry -q
```

Writer evidence on the frozen tree: 198 focused tests pass; the full suite
passes 3,834 tests with 24 expected skips; the integrated draft/close harness passes 17
behavioral checks. Browser verification covers 320,
390, 901, 1024, and 1180px plus 768x480 as the 200%-reflow equivalent; exact
geometry and long-content evidence are in `REVIEW_RECONCILIATION.md`.

## Response format

Return:

1. Verdict: ACCEPT or REJECT.
2. Blocking findings first, each with severity, exact file/line, evidence, and
   the smallest safe correction.
3. Non-blocking observations separately.
4. Verification actually performed.
5. Confirmation that the reviewed implementation-content SHA was
   `887bd087e722562fd4c78f4d75a3b128d1cd74d9` and that no merge, deployment,
   enablement, or live claim was made.

An ACCEPT verdict is review evidence only. It does not authorize merge,
deployment, configuration enablement, broad member authoring, or a live claim.

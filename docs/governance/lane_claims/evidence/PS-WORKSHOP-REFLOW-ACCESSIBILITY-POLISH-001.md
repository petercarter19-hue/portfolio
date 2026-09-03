# PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001 — candidate evidence

## Scope and authority

Pete authorized this package under
`session:01a03e17-a645-7ae0-8da3-164eef90a333/pete-chat-2026-09-02/manage-audit-execution-order-and-parallel-work`.
This is a Bounded repository package with authority through merge. Production
authority is withheld. No deployment, feature enablement, live browser or
member proof, identity, provider, schema, migration, grant, configuration, or
production operation is part of this record.

## Governance lineage

- Claim-only activation candidate
  `94432cc3414005f27197aab5d322c8f9dfc4b119` was independently accepted;
  PR 882 / build 2342 merged it at
  `31798edff5e65bb6cf30e7c254aac524c55df5a2`.
- Pre-registry candidate
  `977533979066c08cb0bd0fae5b0a6fe4a4efea5f` was revised because three
  fixture-only suggestion anchors remained dead focus stops and a desktop
  eyebrow could fragment mid-word. Corrected candidate
  `02f5cf8493e9804c8de3c1d028545d069c70a687` was provisionally accepted
  with zero findings and remains evidence only.
- Deferred Package Registry surface-extension candidate
  `1ea056460fb755ef91e9e9ffa08e698bc2c97f1f` was independently accepted
  with zero findings at `2026-09-03T09:01:11Z`; PR 892 / build 2365 merged
  exactly the one-file claim change at
  `5c2bdf891670893978bbe194ef48b608c9567629`.
- The implementation branch merged that exact current main while preserving
  the corrected provisional candidate in history, then added only the claimed
  Registry row and truthful documentation refresh before final validation and
  review.

## Candidate outcome

Exact reviewed candidate `2ec9a3269dc37db44714c0efbcb03df067564719`
against current-main base `5c2bdf891670893978bbe194ef48b608c9567629`
changes exactly 13 claimed paths: the Package Registry, two initiative
documents, Workshop-local CSS, three claimed partials, three W2 templates, and
three focused test files.

The existing owner-accepted Workshop facelift remains unflagged and unchanged
in composition, copy, and flow. The package establishes one visible Workshop
H1 inside the sole canonical `main#main-content`, with the shared skip link
targeting that main. Under the central manager's bounded interpretation, this
is the required label/ownership relationship for "one H1 and labelled main per
view"; adding an ARIA name or nested main would require excluded shared-shell
work and would be semantically wrong here.

Workshop-local focus, target sizing, reflow, long-text behavior, truthful
native disabled/disclosure states, forced-colors distinctions, reduced motion,
and JavaScript-off forms are explicitly covered. The three fixture-only dead
suggestion anchors emitted by the unclaimed partial are suppressed from layout,
the accessibility tree, and sequential focus by the exact selector
`.wk-suggestion > a[href="#"][aria-disabled="true"]`. The selector is not a
pointer-events workaround and does not affect real links. Flex sizing and
wrapping prevent the suggestion eyebrow from fragmenting mid-word.

The Registry adds `PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001` exactly once
under `current_protect`, locally alphabetized after the existing Voice Visual
Parity entry. `current_protect` changes from 73 to 74 and total from 141 to
142; category counts reconcile to **74 / 33 / 6 / 23 / 6**, all 142 rows are
unique, and no unrelated Registry row or category changes.

Workshop E/F/G and the separate fresh two-member proof remain untouched. The
candidate does not edit shared base or navigation, `_suggestion_card.html`,
routes, authentication, safe return, services, schema, flags, providers,
deployment, identities, live data, or production.

## Validation

- Claimed semantic, polish, and W2 selection: **102 tests run, 1 expected
  skip, zero failures**.
- All `test_workshop*.py` suites: **697 tests run, 3 expected skips, zero
  failures**.
- Package Registry suite: **2 tests run, zero failures**.
- Workshop voice plus shared auth/callback Node suites: **3 files / 49
  behavioral checks / zero failures**.
- Jinja compilation: **26 Workshop templates compiled**.
- Exact requirements Python 3.14 full repository suite: **5,580 tests run,
  35 expected skips, zero failures** in 262.422 seconds.
- Isolated local Chromium proof: **1 test / 18 checks / 18 screenshots / zero
  failures**. It covers signed-out and generic local-authenticated shells,
  populated and empty data, add/review/detail and three W2 states, JavaScript
  off, forced colors, reduced motion, complete keyboard traversal, long text,
  WCAG text spacing, and 1440/1024/768/640/390/320 widths.
- Strict fetched, clean, task-bound write preflight: pass; exact head
  `2ec9a3269dc37db44714c0efbcb03df067564719`, current main
  `5c2bdf891670893978bbe194ef48b608c9567629`, 13 changed paths, ahead 4 /
  behind 0.
- Exact changed-path/claimed-path checks and `git diff --check`: pass.
  Exact current-main-range and full 2,489-commit Gitleaks scans: zero findings.

## Browser and capture evidence

Lifecycle allocation `f86b3c3ed63b18df43908e9c` retains the bounded local
evidence under
`/Users/petercarter/Documents/PeerSlateEvidence/ephemeral_same_task/PS-WORKSHOP-REFLOW-ACCESSIBILITY-POLISH-001/final-browser-proof/2ec9a3269dc37db44714c0efbcb03df067564719`.
The SHA-bound directory contains exactly 18 PNGs totaling 14,332,904 bytes.
Every hash below was recomputed, and the independent reviewer inspected the
desktop and 320px long-text captures. Chromium was `152.0.7977.65`.

| Capture | Bytes | SHA-256 |
|---|---:|---|
| add-768.png | 360630 | `8abc342ae1fd4f862fb0f93f4c13e6be9ffaea516ba5d2c0e812b5c4d6441882` |
| empty-library-768.png | 514310 | `8a6d481a91d0671e58ae1b49fad53cad9d707061a252ca6f99f7c107c1b70aa8` |
| forced-colors-390.png | 1236813 | `a6fe0e7852cbd6908e0af65302bfd071f1ac970b26505f02838c4368bb17ef90` |
| javascript-off-session-390.png | 357281 | `3871d15debdf6a8d5a47b0281494851187baa16c3d36016b1df3328466e747da` |
| keyboard-focus-390.png | 879635 | `57f8cfe5683e010435c426fe57b38cdef1fb9bcc91e037008ee0a9d711d75c95` |
| long-text-spacing-320.png | 1547884 | `022dc7ab6d8dedfdc1196e4d0029884c5d8ee547f5eac224a89fec9ba973f155` |
| populated-library-desktop-1440.png | 1351512 | `bc8b89ce0171d26a08c02f8d1fa94cf3e80c982bccb9a048121b8910f4348f6c` |
| populated-library-phone-390.png | 878590 | `8adc84e68cedbee47fb69be43a9d87ea57ec09827725d83f95290198028d8602` |
| populated-library-tablet-1024.png | 1080002 | `84631012fc194a1dfcd4db4becf4cbccb64c04d81fb26d556b8b04d89105e4c4` |
| populated-library-tablet-768.png | 1001507 | `5836cbd3dba8142490e2a44d693c63eef99daf08a3355880d869fb373c708ed8` |
| populated-library-zoom-200-640.png | 955664 | `816d8250a3d3a52cb107a9eaf4bce0dacfb5e07f352e4b34daa445721a21616a` |
| populated-library-zoom-400-320.png | 867612 | `7905dfcba7950e9ba27e044c44c50b494d43744bdc4231b3d02ab381a346f310` |
| review-768.png | 393768 | `128f65586f2a9284209a8a1aa80f85ef35925ddde17b0ca38af9defc4ef2c8d6` |
| saved-detail-768.png | 346402 | `9d3db149a4898049c01669255d7078a1fb3e0f9ff0c4b649e39f9ab70cdf835c` |
| signed-out-shell-1440.png | 1470671 | `186b8f29b2342a50992e4326112550001bb69eba3dedf0e2e3fb07487edc1e76` |
| work-opening-390.png | 341986 | `c098301fc74b743282521589266e56306fe8c0ffc9ff666f342e33e64c02c617` |
| work-review-390.png | 386674 | `58cc4f21fd680dcc4d6abeac6f7162965468fd8bc27226247561f25c39403b1c` |
| work-session-390.png | 361963 | `435f325f71582cdfd52bfe8225673dcd04c9905bb509421097e7a0d91afef4b9` |

Every screenshot has corresponding DOM, layout, semantic, or interaction
assertions; screenshots are supplementary rather than the sole proof. The
browser worker uses only isolated local fixtures and a generic local
development identity. It contacts no live host, identity, provider, or
credential, and restores its Flask configuration, limiter, patches, server,
instance directory, environment, and process state.

## Independent review

Independent provisional review revised candidate
`977533979066c08cb0bd0fae5b0a6fe4a4efea5f` for the dead suggestion stops and
eyebrow fragmentation described above. Corrected pre-registry candidate
`02f5cf8493e9804c8de3c1d028545d069c70a687` was provisionally accepted with
zero findings but remained unmergeable until the governed Registry extension.

Independent final review ACCEPTed exact candidate
`2ec9a3269dc37db44714c0efbcb03df067564719` against exact current main
`5c2bdf891670893978bbe194ef48b608c9567629` with zero findings. Reviewer:
`agent:/root/interview_studio_operability`; reviewed at
`2026-09-03T09:27:19Z`. The reviewer independently verified exact Azure refs,
all 13 claimed paths, byte-identical accepted implementation/test blobs,
Registry uniqueness/counts, semantic and styling boundaries, complete focused
validation, 18 valid SHA-bound captures, lifecycle/preflight state, diff, and
range/full-history secret scans. Acceptance authorizes repository merge only.

## Release truth

This evidence binds an immutable repository candidate. It does not state or
imply that the Workshop change is deployed, enabled, production-ready, or
live-proven. Any deployment, feature configuration, or authenticated live
proof requires a separate claimed package and explicit action-specific
authority.

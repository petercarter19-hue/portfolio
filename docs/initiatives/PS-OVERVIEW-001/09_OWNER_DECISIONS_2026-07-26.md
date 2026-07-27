# Owner decisions — 2026-07-26

## 1. Authority and boundary

Pete approved the page-purpose inventory and the six first-release decisions
below during the owner-review gate on 2026-07-26.

This record controls over earlier open-choice language in this package. It
authorizes ChatGPT to create production-intent visual candidates. It does not
lock a visual file, authorize architecture or runtime implementation, change
the current résumé, or activate a member-facing capability.

## 2. Approved inventory

Pete approved
`02_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md` as the content and control
inventory for the visual-creation gate.

Visual candidates may omit optional items according to their declared empty
states, but they may not add a new meaningful public item, owner control,
action, destination, claim, or state without returning to Pete.

## 3. Approved first-release decisions

| Decision | Owner-approved result |
| --- | --- |
| Public audience | The Overview inherits the public résumé audience. It cannot be broader. A separately selectable Overview audience is deferred. |
| Proof metrics | Metrics remain optional. The member supplies the exact displayed value, either by direct entry or an explicit value in the current AI request. There is no metric source-backing, evidence-linking, verification, or provenance-state system in the first release. The public metric is an authored Overview claim, not a canonical fact or a PeerSlate-verified claim. |
| AI and metric values | AI may preserve an exact member-supplied value and help format or shorten its label. It may not invent, infer, calculate, round, embellish, change, or silently substitute the value. Numeric tokens are immutable in an AI wording proposal unless the member explicitly supplies a replacement value. |
| Public length | Four to six major content bands is the normal target. Eight major content bands is the absolute first-release maximum. The identity hero and optional proof band do not count toward that maximum. Empty optional blocks render no wrapper or gap. |
| Style names | The member-facing names are **Story & Career** and **Work & Impact**. Story & Career remains the flagship/recommended starting style. |
| Actions | The hero primary action is **Connect**. The hero secondary action is **View résumé**, targeting the actual résumé below on the same page. **Résumé PDF** appears once in the left Context Rail. **Ask [Name] AI** or **Ask Slate AI** appears once in the right contextual AI rail according to public/private context. Mobile uses compact Sections and Ask AI controls or sheets. |
| Wide geometry | The first production-intent visual candidate starts at `min(92vw, 90rem)` at normal scale, with no CSS `zoom` or transform fitting and the contextual section control outside the center canvas. Full-browser 2560- and 3840-pixel review may lead Pete to widen or otherwise adjust the exact stage before file/hash lock. |

The page-purpose inventory is an approval in addition to the six choices:
audience, metrics, public length, style names, actions, and wide geometry.

## 4. First-release metric data boundary

A proof metric is bounded Overview projection content:

- a required member-supplied display value;
- a short member-authored or member-accepted label;
- an optional validated public destination; and
- normal draft, preview, publish, version, hide, reorder, and remove behavior.

It has no metric-source selector, source record, evidence attachment,
verification badge, or sourced/member-confirmed/unsupported provenance state
in the first release. Existing source and corrective-supersession contracts
continue to govern record-linked résumé, Story, Project, media, and other
eligible blocks; they do not create a hidden metric-provenance system.

AI may receive a value only because the member typed that exact value in the
metric field or explicitly supplied it in the current request. If a request
does not contain an exact value, AI must leave the value field unchanged and
ask the member for it. AI label editing treats the existing value as locked.

## 5. Deferred and review-time topics

The following are intentionally deferred rather than silently implemented:

- source-backed or evidence-linked proof metrics;
- metric verification and provenance states;
- a separately selectable Overview audience;
- additional style names or visitor style switching; and
- any public-length or geometry change learned through real-member testing.

Source-backing may be reconsidered after the basic editor and public experience
are working and have been reviewed live with Pete and other members. A future
change requires its own product decision, data migration treatment for existing
authored metrics, UX states, privacy review, tests, and visual acceptance.

The four-to-six target, eight-band maximum, and starting wide geometry are
first-release guardrails. Pete may revisit them during visual review,
implementation testing, and live real-member usability review. A change is not
implicit merely because a fixture is unusually sparse or rich.

## 6. Visual-selection result

Pete reviewed the public rich, sparse, narrow-desktop, and mobile directions
for Story & Career and Work & Impact plus the first-time setup, proof-point
editor, add-section catalog, AI-suggestion review, consolidated rails/public
Ask AI, and Review & Publish states.

Those approvals select one composite visual authority:

- Story & Career remains the flagship and recommended starting style;
- Work & Impact remains the business-first alternate;
- approved states and hashes are recorded in
  `10_VISUAL_AUTHORITY_LOCK_2026-07-26.md`;
- the early generated `story-and-career-wide-standard` and
  `work-and-impact-wide-standard` files are superseded generation history and
  do not control implementation; and
- package contracts control missing-content, large-text, focus, failure, and
  other states not literally shown in a single raster.

This selection does not mean that an illustrative raster is live product
content, that generated imagery is member evidence, or that fixture wording is
reusable product data.

## 7. Final shell, AI, editor, and publication decisions

Pete made these additional controlling decisions during the visual review:

| Topic | Owner-approved result |
| --- | --- |
| Page regions | Wide desktop uses a distinct left local-section rail, dominant center Overview/résumé stage, and right contextual AI rail. Both rails may remain sticky while the center scrolls when sufficient width exists. |
| Left rail | Preserve the member portrait/name. Replace duplicate route navigation with **RÉSUMÉ SECTIONS**: Overview or Summary, Impact, Skills, Experience, Credentials, then one separated Résumé PDF action. Entries navigate within the current page. |
| Right rail | Use contextual AI rather than duplicate section links. Public member pages use **Ask [Name] AI**; signed-in private workspaces use **Ask Slate AI**. |
| Public grounding | Ask [Name] AI may use approved public member information only. It cannot access private Slate information. |
| Private grounding | Ask Slate AI may use only the authenticated member's authorized private context for the current workspace/task. It remains proposal-only. |
| Cross-product direction | The contextual AI-rail pattern should be available across purposeful Slate/Studio surfaces, but every surface requires its own package, permitted-context contract, visual authority, and acceptance. This package does not implement those adoptions. |
| Responsive rails | The center stays dominant. The AI rail becomes a drawer/sheet before it squeezes the center. Mobile keeps a prominent Ask AI action and collapses section depth into the approved Sections control/chip treatment. |
| Résumé integration | The current detailed résumé remains below the Overview. The published Overview replaces the current Summary opening; unpublish restores Summary. |
| Editor | Manual editing is complete. Add, edit, hide, remove, reorder, destinations, preview, save, and publication do not require AI. Desktop inspectors recompose to full-width mobile sheets/steps. |
| Review and publish | The member sees the exact destination, what changes, what remains, included/omitted sections, desktop/mobile preview, and explicit **Publish Overview** action. AI cannot publish. |
| First-release metrics | Remove all source-backed/member-confirmed/provenance UI. Revisit only through a later product/data/trust package after live testing. |

These decisions are incorporated in
`11_FINAL_ARCHITECTURE_CONTRACT_2026-07-26.md`, which controls over earlier
separately-gated-rail or duplicate-rail language inside this package.

## 8. Next gate

The architecture and visual lock are complete. Pete explicitly approved the
corrected mobile proof-point editor on 2026-07-26. Complete package-local
visual/hash validation and diff review; merge this documentation/design package
through Azure; then start the separately bounded generic renderer foundation
in `implementation-slice-1/README.md` only after separate activation.

The visual-authority branch remains non-runtime. The first implementation slice
may not change the current public résumé, add persistence or publication, or
claim a member-facing Overview exists.

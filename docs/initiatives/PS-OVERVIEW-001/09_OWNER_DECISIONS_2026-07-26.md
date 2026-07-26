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
| Actions | The hero primary action is **Connect**. The hero secondary action is **View résumé**, targeting the actual résumé below on the same page. **Download PDF** and **Ask [Name] AI** are shared contextual controls outside the hero. Actions appear once; mobile may place the shared controls in one compact accessible menu. |
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

## 6. Next gate

ChatGPT creates both complete production-intent visual/state sets from this
approved contract. The set must show the exact action hierarchy, metric manual
editing and AI value lock, no-metric and one-metric states, the approved public
density, responsive reflow, and measured full-browser wide-desktop geometry.

Pete then reviews and locks exact durable files and SHA-256 hashes. Only a
separate activated implementation package may authorize runtime work.

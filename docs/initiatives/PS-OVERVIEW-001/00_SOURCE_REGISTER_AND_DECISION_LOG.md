# Source register and decision log

## 1. Why this record exists

Pete supplied two Overview concepts and a Claude system-requirements draft. This
record preserves the exact inputs while separating useful requirements from
ideas that conflict with Pete's correction, PeerSlate's current authority, or
the goal of a reusable multi-user product.

No input below is production visual authority by itself.

## 2. Exact source register

| ID | Source | Dimensions / format | SHA-256 | Use |
| --- | --- | --- | --- | --- |
| S-1 | `source/story-and-career-owner-concept-2026-07-25.png` | 941 × 1672 PNG | `0F2F70EB8AB4E417CE6F2A0CEB3F47BC00C7EEAD9BFFC78A9B6C6D3D081613C4` | Flagship Story & Career direction |
| S-2 | `source/work-and-impact-owner-concept-2026-07-25.png` | 864 × 1821 PNG | `B5276B1728B80A17BE395DD4F1ABBB9BEC74346AEF8D928E9CC8DFA7B59412E6` | Alternate Work & Impact direction |
| S-3 | `source/claude-overview-system-requirements-draft-2026-07-25.txt` | UTF-8 text | `09E026EAE767CF0B21F262F9D2236E5ABE360631162FAF049AE7D6219979DD43` | Requirements input, not controlling authority |

S-1 and S-2 are portrait editorial boards. Their raster widths and aspect
ratios do not specify a CSS `max-width`, browser viewport, or outer production
silhouette. The exact wide-desktop correction is recorded in
`08_WIDE_DESKTOP_WIDTH_AMENDMENT.md`.

## 3. Pete's controlling corrections

The following owner statements control over visual implications in either
concept or assumptions in the Claude draft:

- The Overview is above the real résumé; the illustrated Full Résumé block is
  discarded.
- The actual site rail is outside the center canvas. The Business concept's
  apparent left column is not the permanent page rail.
- Skills replaces Core Tools and appears before Education, Certifications, and
  Awards.
- Education, Certifications, Awards, Story, personal, future-direction, and
  specialty content must be optional. Their absence cannot leave gaps.
- Every summary that has additional public detail should offer a specific,
  working destination into the actual résumé or another eligible public
  surface.
- Manual and AI-assisted setup are equally valid; no member should need a
  developer or AI to maintain an Overview.
- The Portfolio concept is the preferred combined résumé/portfolio direction;
  the Business concept remains valuable as a second results-forward option.
- The tall concepts cannot be treated as browser-width authority. The Overview
  must use the full resolved résumé center-content column, with readable text
  measure managed inside its blocks.

## 4. Claude draft reconciliation

### Adopt

| Claude idea | Decision and reason |
| --- | --- |
| Overview is a projection, not another truth store | Adopt. Factual blocks reference canonical records or governed projection wording with lineage. |
| Finite block families and a computed layout | Adopt. A structured composer is necessary for reliable quality and no-gap behavior. |
| Derived versus authored content | Adopt with the term **record-linked**, **authored**, or **hybrid** so a block can combine selected facts with presentation copy. |
| Empty blocks do not render | Adopt. Empty, hidden, unauthorized, invalid, or unpublished blocks create no public wrapper or reserved space. |
| Character/item budgets and specific overflow links | Adopt as initial design targets. Final values must be validated against the locked typography. |
| Real anchors, keyboard focus, reduced motion, and no-JavaScript meaning | Adopt. These are part of the destination contract, not optional polish. |
| Private draft, exact visitor preview, and atomic publication | Adopt. The current public revision remains unchanged while editing. |
| AI is optional, source-grounded, proposal-only, and cannot publish | Adopt. Accepted language enters the private draft; it does not become canonical fact. |
| Server-derived edit authorization | Adopt. Owner controls and private metadata are never delivered in the public representation. |
| Drag reorder requires a keyboard/structured equivalent | Adopt. Reordering is sequence control, not arbitrary spatial design. |

### Refine

| Claude idea | Refined decision |
| --- | --- |
| A permanent internal rail plus band column | The Overview is one center canvas. Work & Impact may use a wide-screen supporting column, but it reflows normally and is never the site rail. |
| Stat strip permits 0 or 2–4, never 1 | Permit one truthful proof item and render it as a featured proof treatment. Early-career members must not be forced to invent a second metric. |
| Thin Education/Certification/Award cards automatically merge | Each category remains semantically honest. One degree may render as a confident compact Education preview; count-aware layout may place groups together without renaming facts into a misleading category. |
| The system automatically selects Full/Compact/Starter and prevents member choice | The member explicitly chooses Story & Career or Work & Impact in the draft. Each style has deterministic sparse/standard/rich arrangements; content readiness may block a broken publication but does not silently change the member's selected style. |
| AI may never fill a stat value | Refine for the first release: the member supplies the exact value directly or explicitly in the current AI request. AI may preserve that exact value and propose label wording, but may not derive, retrieve, calculate, round, embellish, or change it. No metric source-backing or provenance-state system is included. |
| Public and owner rendering use the same payload with `editable: true` | They may share an internal rendering contract, but the authorized owner editor and public viewer receive different representations. The public response contains no owner controls, private sources, draft content, or edit metadata. |
| Authored AI text is not saved until an explicit Save | Private draft autosave is allowed and preferred. Accepting an AI proposal changes only the private draft. Publication is always a separate explicit action. |
| Sticky internal rail after its content ends | Defer to future visual design; it is not required and must not compete with the real context rail. |

### Reject

| Claude idea | Rejection reason |
| --- | --- |
| Public Starter text such as “your Overview grows as you add” | Owner guidance belongs in the authenticated editor. Public visitors see a truthful published Overview or the résumé begins immediately; they do not see setup prompts. |
| Required Executive Brief pinned first for every style | Story & Career may lead with identity and Story; Work & Impact may lead with a brief. Neither authored block is universally required. |
| One fixed left-rail card sequence as the product model | It mistakes one concept's visual composition for permanent information architecture and conflicts with Pete's center-canvas correction. |
| Arbitrary member sizing or positioning | That would re-create broken layouts and developer dependence. Overview composition uses order and approved emphasis variants only. |
| Generic `More`, hidden overflow, clipped sentences, fixed-height text, or card scrollbars | These conceal meaning and create inaccessible, inconsistent public results. |

## 5. Decisions made by this package

| Decision | Result |
| --- | --- |
| Product count | One Overview system |
| Style count for first implementation target | Two: Story & Career and Work & Impact |
| Recommended default | Story & Career |
| Public versions visible at once | One |
| Canonical data stores added | None |
| Manual editor | Required and complete without AI |
| AI path | Optional proposal path using the same editor |
| Freeform geometry/CSS/HTML | Not supported |
| Public empty states | Omitted; résumé starts immediately when no Overview is published |
| Full résumé duplication above the résumé | Prohibited |
| Existing résumé Summary | Absorbed/replaced when Overview publishes; restored as fallback after no publication/unpublish |
| Existing contextual section control | Current right ribbon stays until a separately gated left Context Rail migration; first entry is Overview or Summary according to state |
| Public withdrawal | Explicit owner-controlled atomic unpublish with retained history and Summary fallback |
| Corrected canonical fact | Corrective supersession fails the old public claim closed; no replacement wording auto-publishes |
| Story Spotlight | Requires eligible published Story; standalone narrative uses Flexible Spotlight |
| Current concepts' status | Owner-selected direction inputs, not locked production authority |
| Wide-desktop canvas | Overview root fills the resolved résumé content column; no second arbitrary narrow page stage |
| Wide-stage visual candidate | Start ChatGPT visual creation at `min(92vw, 90rem)` at normal scale, with the contextual control outside the center canvas; Pete's exact lock controls |
| Wide-desktop evidence | Full-browser 1440 × 900, 1920 × 1080, 2560 × 1440, and 3840 × 2160 CSS-pixel views are required before visual lock |
| Reading measure | Controlled inside cards/bands; it never justifies narrowing the entire Overview |
| Fit technique | CSS `zoom` or transform scaling may not be used to make the future Overview fit |
| Shared-shell width | The older planned `PS-SHELL-001` 1120–1200-pixel estimate does not narrow or block Overview visual creation. Reconcile the exact Pete-locked Overview geometry with the shared shell before runtime implementation. |
| Page-purpose inventory | Pete approved `02_PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md` on 2026-07-26 |
| Public audience | First release inherits the public résumé audience and cannot be broader |
| Proof metrics | Optional member-authored Overview claims; no source-backing, evidence-linking, verification, or provenance-state system in the first release |
| AI and proof values | AI may preserve an exact member-supplied value and edit its label; it may not invent, infer, calculate, round, embellish, or change the value |
| Public content length | Four to six major content bands normally; eight absolute maximum; hero and optional proof band do not count |
| Member-facing style names | Story & Career and Work & Impact |
| Public action placement | Hero: Connect primary and View résumé same-page secondary. Shared context: Download PDF and Ask [Name] AI. No duplicates; compact accessible mobile menu permitted |
| Starting visual geometry | Pete approved `min(92vw, 90rem)` at normal scale as the first candidate, subject to exact full-browser visual review and later file/hash lock |

## 6. Owner approvals recorded 2026-07-26

Pete approved:

1. the exact meaningful-item inventory;
2. the public résumé audience for the first release;
3. optional member-entered proof metrics with no first-release source-backing
   or provenance system and with AI unable to invent or alter values;
4. four to six major content bands normally and eight maximum, excluding the
   hero and optional proof band;
5. Story & Career and Work & Impact as the member-facing style names;
6. Connect and View résumé in the hero, with Download PDF and Ask [Name] AI in
   shared contextual controls; and
7. `min(92vw, 90rem)` at normal scale as the first wide visual candidate, with
   exact 2560-/3840-pixel review before visual file/hash lock.

The remaining owner gate is the exact ChatGPT-created visual/state set for both
styles. See `09_OWNER_DECISIONS_2026-07-26.md`.

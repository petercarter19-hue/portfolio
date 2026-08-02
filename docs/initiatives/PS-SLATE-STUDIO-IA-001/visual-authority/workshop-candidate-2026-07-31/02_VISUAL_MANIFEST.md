# Visual manifest and candidate status

## Authority statement

These files are a structurally complete **candidate visual set** created during the ChatGPT visual-creation round and reviewed iteratively by Pete.

They are not yet a Pete-locked, hash-pinned implementation authority. Claude must not call them implemented, approved for code, deployed, or live.

| File | Dimensions | Purpose | Current status | SHA-256 |
|---|---:|---|---|---|
| `images/00-reference-current-interview-studio.jpg` | 1280×853 | Current Interview Studio quality/composition reference only | Reference; not Workshop authority | `ED134F6EF813530F21553500587ABC27EEBDDB9998542811F752832B141C7E4F` |
| `images/01-workshop-opening.jpg` | 1280×910 | Personalized Spark and direct start | Structurally accepted candidate | `D0250CB5A452B964576EA09A26DA2964EF6088EF5AC4C03F22C365D4BCFBF0C6` |
| `images/02-workshop-type-speak.jpg` | 1280×910 | Focused Type/Speak contribution | Structurally accepted candidate | `FAB8416945AF48B1D7524398284A95784715E013720FC244071366BE3BCC4219` |
| `images/03-workshop-ai-review.png` | 1487×1058 | Original words, interpretation, evidence, and focused improvement | Structurally accepted candidate; set-wide audit pending | `717C8CE1F544A9D3FC02DA4D18E0C4CBFB03797E92DC422874396DF6EEA0F488` |
| `images/04-workshop-saved-privately.png` | 1487×1058 | Private-save completion and optional résumé-draft offer | Structurally accepted candidate; set-wide audit pending | `25B2F813A0396EFE8194478D5A2316947346EF5D5E1424A8682CF48BE8C55069` |
| `images/05-workshop-my-information.png` | 1486×1058 | Search, inspect, edit, permissions, uses, and suggestions | Structurally accepted candidate; set-wide audit pending | `0C80AFEDCC9636AB9BC8EA582E06D17641ABCBCE05B40564556CF438342C2B63` |

## Known set-wide issues

1. The first two Workshop screens are 1280×910 JPEGs with a browser frame; the last three are approximately 1487×1058 PNGs. Exact comparable-state dimensions and browser chrome require a later visual-lock pass.
2. Global navigation shown in generated Workshop images is placeholder. It omits or changes existing navigation and must not be accepted through visual inference.
3. `View private profile` is generated placeholder language and is not an accepted replacement for the current site's profile/public-page control.
4. The final palette and exact background strength are not locked. Navy has been rejected; abstract gray-blue is the current candidate family.
5. Responsive/mobile, keyboard focus, 200% reflow, long-content, empty, loading, error, AI-unavailable, permission-denied, and reduced-motion visuals do not yet exist.

## Screen-specific review items

### Opening

- Confirm whether the page subtitle is final.
- Confirm that the Spark explanation and right contextual rail are not redundant.
- Confirm navigation placement outside this visual set.

### Type/Speak

- Confirm that `Use as context` shows selected/unselected and unavailable states.
- The source line beneath related information may be ambiguous and should be tied to the current answer rather than all related items.
- Confirm voice recording, transcription, retry, and AI-unavailable behavior later.

### AI Review

- Confirm the hierarchy between `Add the missing result` and `Improve with AI`.
- Confirm whether the `Standout evidence` star is sufficiently non-gamified.
- Ensure the original wording remains genuinely preserved and separately editable.

### Saved Privately

- Privacy and AI-use information is repeated across the left rail, central item, and right rail.
- `Create résumé draft` is visually dominant and may compete with the message that the private save is already a complete success.
- Confirm whether `Close for now` should receive stronger visual weight.

### My Information

- Area and status filters need independent, unmistakable selection states. The current color treatment can make `All`, `Confirmed`, and `Suggested` appear simultaneously active.
- Confirm that the private-library view does not drift into Settings.
- Suggestions must always cite actual member-provided evidence, never cohort stereotypes or unsupported inference.
- Confirm archive, delete, restore, affected-use review, and AI-use permission behavior.


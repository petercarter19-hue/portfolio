# Bible v2.7 Template Distillation

## Control purpose

This record proves that Bible v2.8 is a bounded authority update to the
approved Bible v2.7 document system, not an unrelated visual rewrite. It also
identifies which inherited document characteristics were deliberately
preserved and which current requirements were deliberately superseded.

## Binary lineage

| Role | File | SHA-256 | Bytes |
|---|---|---|---:|
| Controlled template | `docs/governance/PeerSlate_Company_and_Product_Bible_v2.7.docx` | `CEEF99F1A84BF293217AD6D302A2B15E19B18104896DE7F8ED560416DEAF1836` | 10,024,925 |
| Generated authority | `docs/governance/PeerSlate_Company_and_Product_Bible_v2.8.docx` | `47F9771C29A3FAEA18858865F402DF0E342840DAD80ECF4650B8ABCC537DE963` | 10,030,018 |

`build_authority_documents.py` reads the v2.7 binary, makes uniquely anchored
OOXML changes, appends Appendix O from the repository-local amendment source,
and writes v2.8. It fails when an expected anchor is missing, duplicated, or
when required/forbidden current text does not pass verification.

## Template characteristics preserved

- One portrait US Letter section.
- Margins: left/right 0.72 inches, top 0.68 inches, bottom 0.64 inches.
- Ten inline images and their relationships/media bytes.
- Ninety-two tables and their geometry.
- Styles, theme, numbering definitions, relationships, media, headers,
  footers, and section geometry except for bounded current identity text.
- The 32-member DOCX package structure.
- Existing TOC/PAGE field architecture: 144 `PAGEREF` fields and one `PAGE`
  field.

Only these package parts changed:

- `docProps/core.xml`;
- `word/document.xml`;
- `word/header2.xml`;
- `word/footer1.xml`; and
- `word/footer2.xml`.

Field starts are marked dirty so Microsoft Word can refresh cached navigation
and page references. This does not replace the field structure with hardcoded
page numbers.

## Deliberate v2.8 changes

- Current version, authority, supersession, and running-identity text now name
  Bible v2.8.
- Capture is an action/context-preserving composer, not a page, tab, or
  destination.
- `Save Moment` creates one private source-linked member-saved canonical Moment
  immediately; member-authored text has no mandatory AI review or promotion
  gate.
- Owner-Journal membership is derived from the canonical Moment and cannot
  create a copied Journal fact body.
- Owner-complete and audience-authorized Journal projections are separated.
- Journal and My Story share exact records but retain distinct jobs.
- `Use This Moment` includes both finite shortcuts and a complete accessible
  chooser of every currently supported and authorized purpose.
- Replay/resurfacing, private Momentum, Prompt/Ritual, What PeerSlate Noticed,
  Slate Mirror, Ask Slate AI, later messaging, and early legal gates receive
  constitutional boundaries.
- Three stale image descriptions were corrected through exact fail-closed
  anchors so their alternative text no longer describes superseded Capture or
  review-gate behavior.
- Appendix O records the complete owner-approved covenant without rewriting
  historical decision evidence as though it had never existed.

Heading counts changed from H1/H2/H3 `38/120/1` to `39/127/1`. One semantic
data-table header was added, changing marked header rows from 24 to 25. The
remaining unmarked tables are reviewed inherited presentation/layout
structures; their treatment is recorded in the consolidated verification
report.

## Inherited formatting debt

The style linter reports 863 directly formatted runs and 958 directly
formatted paragraphs. These counts are inherited from the controlled template,
not newly introduced style-system replacements. Its first heading-like
warnings are cover and TOC display lines rather than missing body heading
semantics. A future document-modernization package may normalize inherited
formatting, but doing that inside this authority update would create a much
larger and less auditable visual change.

## Distillation result

The v2.7 visual/document system remains recognizable and structurally intact.
The v2.8 delta is traceable to the July 20 owner decisions and resolves current
product contradictions without silently claiming runtime implementation.

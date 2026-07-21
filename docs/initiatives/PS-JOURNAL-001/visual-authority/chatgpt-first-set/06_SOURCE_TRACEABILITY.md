# Source Traceability and Decision Confirmation

## Decision

The small visual-authority packet is the correct approach for the first
ChatGPT image round.

The current PeerSlate authorities require a complete, truthful,
production-intent design set. They do not require every source document to be
uploaded to the image generator. A distilled product-truth block plus a small
mapped reference-image set better protects the non-negotiable architecture and
reduces unrelated visual drift.

The full governing documents remain controlling for implementation and final
acceptance. This folder is a portable design brief derived from them; it does
not supersede them.

## Current document integrity

- Bible: `docs/governance/PeerSlate_Company_and_Product_Bible_v2.8.docx`
- Bible SHA-256:
  `47F9771C29A3FAEA18858865F402DF0E342840DAD80ECF4650B8ABCC537DE963`
- Roadmap:
  `docs/governance/PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.7.docx`
- Roadmap SHA-256:
  `899F0054483E886F79AACB4115AE0E160ACC44FA3BFFE5EEA2882A5C70EE6A83`

The hashes match `docs/governance/CURRENT_BASELINE.yaml` at the authoritative
Azure `origin/main` base used for this handoff.

## Traceability by handoff rule

| Handoff rule | Controlling source |
|---|---|
| Capture is an action, not a destination | Bible v2.8 `PS-CORE-CAP-001`; `PS-JOURNAL-001` `PS-JRN-CAP-001` through `PS-JRN-CAP-004`; `PS-JRN-IA-001` through `PS-JRN-IA-006` |
| Type and Speak are first-class | `PS-JRN-CAP-005`, `PS-JRN-CAP-008`, `PS-JRN-CAP-009`; Owner Visual Integrity Standard V0 |
| Save Moment is the single commit | Bible v2.8 `PS-CORE-CAP-002`; `PS-JRN-CAP-006`; `PS-JRN-MOM-001` through `PS-JRN-MOM-006` |
| One private canonical Moment; derived Journal membership | Bible v2.8 `PS-CORE-JRN-001`; `PS-JRN-JRN-001` through `PS-JRN-JRN-004`; `03_DATA_AUTHORIZATION_AND_LIFECYCLE.md` |
| No automatic publication or downstream mutation | `PS-JRN-MOM-010`; `PS-JRN-USE-002` through `PS-JRN-USE-013` |
| Owner Journal complete; other views authorized projections | Bible v2.8 `PS-CORE-JRN-002`; `PS-JRN-AUD-001` through `PS-JRN-AUD-018` |
| Journal and My Story distinct | Bible v2.8 `PS-CORE-STY-001`; `04_JOURNAL_MY_STORY_AND_PROJECTION_BOUNDARY.md`; Owner Story Composition Standard |
| Navigation remains open | Bible v2.8 `PS-CORE-GOV-015`; Roadmap v2.7 Navigation and deferred items; `PS-JRN-IA-001` through `PS-JRN-IA-008` |
| Required desktop/mobile/state completeness | Owner Visual Integrity Standard V1; `02_EXPERIENCE_AND_INFORMATION_ARCHITECTURE.md`; `PS-JRN-CAP-014`; `PS-JRN-JRN-014` |
| Deep Navy Gold and editorial quality | Current Bible/AGENTS design foundation; Owner Visual Integrity Standard; approved owner visual baseline |
| Generated boards are not implementation or live proof | Owner Visual Integrity Standard truth boundary and V0 through V4; `CURRENT_STATE.md` honest boundaries |

## Why the full Bible and Roadmap are not first-round uploads

The Bible and Roadmap contain company-wide architecture, sequencing,
governance, AI, legal, return-value, messaging, and later-product material.
Most of it is valid but not necessary to compose the first four Journal
screens. Giving all of it equal weight to an image conversation can cause the
model to:

- combine later features into the private Journal core;
- design navigation that is deliberately still open;
- treat public Journal, return services, Ask Slate, or messaging as current;
- blend unrelated Home, Interview, Photo, Board, résumé, and Story packages;
  or
- reproduce historical concepts that the July 20 one-Journal decision
  superseded.

The context text includes every Bible/Roadmap rule that changes the first-set
composition. The full documents should be consulted by managers and engineers,
not treated as an undifferentiated image prompt.

## OpenAI workflow basis

OpenAI's current image-generation guidance recommends clear descriptions of
purpose, subject, action, setting, style, and constraints; a small number of
explicitly mapped reference images; and targeted revisions rather than broad
multi-variable re-prompts. It also recommends keeping in-image text short and
specific. This handoff follows that pattern while adding PeerSlate's stricter
product-truth and visual-integrity requirements.

Official references:

- `https://openai.com/academy/image-generation/`
- `https://help.openai.com/en/articles/11084440-chatgpt-images-faq`

## Final confirmation

Proceed with this packet for Round 1. Do not call the result accepted visual
authority until:

1. Pete selects and approves a direction;
2. the designated manager records the exact accepted image files;
3. the complete required state set is produced;
4. truth, responsive, accessibility, and failure-state review passes; and
5. the package records visual status as Accepted.

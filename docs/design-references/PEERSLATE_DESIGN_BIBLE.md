# PeerSlate Design Bible

**Version:** 0.3
**Status:** Approved Foundation C
**Product statement:** Your Work. Your Story. Your Future.

## Product standard

PeerSlate is an evidence-backed professional story and growth platform. It is not a generic portfolio, resume builder, social feed, dashboard, or AI wrapper. Members capture work, connect it to proof, shape it into stories, practice communicating it, and publish only what they choose.

Every page is a different room in the same premium building: shared navigation, typography, surfaces, spacing, evidence language, and interaction grammar; distinct purpose and atmosphere.

## Experience modes

1. **Public Experience:** cinematic product storytelling that demonstrates PeerSlate through real product objects.
2. **Signed-in PeerSlate:** direct, productive member workspace for capture, goals, Slate Feed, Slate Board, connections, and AI guidance.
3. **Public and Recruiter Slate:** controlled, evidence-backed professional story. Only approved, audience-appropriate material is visible.

## Foundation C

- **Editorial display:** Newsreader.
- **Product UI:** Inter.
- **Product/action indigo:** `#4F5BD5` with white text (5.54:1 contrast).
- **Connection azure:** `#4EA3FF`.
- **AI cyan:** `#2EC8D3`.
- **Evidence amber:** `#D7A33E`.
- **Midnight ink:** `#0A1B36`.
- **Cloud white:** `#F6F8FC`.
- **Signature gradient:** Cyan to Azure to Indigo. Violet is optional atmosphere only.

Core product pages favor luminous, restrained light environments with glass hierarchy. Dark scenes are intentional cinematic moments, not the default. Pink and rose are not part of the final semantic interface palette: never use them for buttons, navigation, card borders, labels, progress, or primary gradients.

## Experience principles

- Give every screen one unmistakable purpose.
- Make the product object more important than explanatory copy.
- Lead claims naturally to approved evidence.
- Be cinematic, not theatrical; motion creates continuity without delaying comprehension.
- Use editorial clarity for emotion and product precision for interfaces.
- Preserve calm density through hierarchy and progressive disclosure.
- Make privacy, source grounding, evidence status, and AI synthesis visible.
- Design for every Slate, not one demo profile.
- Enter information once and render it everywhere from approved structured data.

## Multi-tenant and trust requirements

- Pete's Slate is User 001 and reference/demo data, never product logic.
- Reusable components must not hardcode a member's employers, dates, metrics, skills, education, role counts, or evidence.
- Every profile-owned record is tenant-safe and carries profile ownership, source/provenance, visibility, approval state, and stable identity metadata.
- Private or unapproved evidence must never appear in public, recruiter, cross-member, or AI contexts without authorization.
- AI extraction and voice input create reviewable drafts. A member approval is required before data becomes approved; publication is a separate explicit action.
- Voice input must produce an editable transcript and structured change preview before a member approves it.

## Shared structured data rule

The Resume Ledger, Career Constellation, public Slate, AI grounding, skills, and evidence views all render from the same structured, multi-tenant data. A visual presentation may vary; its underlying ownership, source, visibility, and approval rules may not.

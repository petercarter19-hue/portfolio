# PeerSlate Early Legal and Product-Site Readiness Standard

_Owner direction: July 20, 2026. Governance checklist, not legal advice._

## Purpose

Trust cannot be postponed until launch. PeerSlate shall begin product, policy,
site, and operational readiness while private core features are being built,
then obtain qualified legal/security review before higher-risk capabilities are
made broadly available.

Internal completion of this checklist does not mean counsel approved the
product, a security assessment passed, or a legal requirement is satisfied.
Each gate must name its actual reviewer and evidence.

## PS-LEGAL requirements

- **PS-LEGAL-001:** Maintain a plain-language data inventory covering account,
  Capture source, text, transcript, audio/media, Moment, Journal, projection,
  audience/access, AI input/output, upload/OCR, message, telemetry, support,
  moderation, and security data.
- **PS-LEGAL-002:** For every class, record purpose, owner/controller role,
  collection source, system location, subprocessors, access roles, retention,
  export, correction, deletion, backup/cache/index propagation, and security
  controls.
- **PS-LEGAL-003:** Public Privacy, Terms, Acceptable Use, accessibility/contact,
  and support links shall be accurate, reachable, versioned, dated, and matched
  to actual behavior before broad account availability.
- **PS-LEGAL-004:** Cookie/tracking consent and disclosures shall reflect the
  trackers actually present by geography; no banner shall claim controls the
  product does not enforce.
- **PS-LEGAL-005:** AI disclosures shall distinguish model assistance,
  deterministic product decisions, source grounding, uncertainty, provider
  processing, retention, member review, and prohibited automatic actions.
- **PS-LEGAL-006:** Voice/audio disclosures shall cover recording consent,
  retention, transcription, playback, provider processing, deletion, and
  jurisdictional constraints. Synthetic/cloned voice requires a separate gate.
- **PS-LEGAL-007:** Upload terms and UI shall address ownership/license,
  third-party confidential/copyrighted content, malware/content limits, OCR/
  extraction, retention/deletion, provider processing, and prohibited uploads.
- **PS-LEGAL-008:** Public/member content shall have reporting, takedown,
  copyright/IP contact, impersonation, harassment, and appeal/escalation paths
  proportionate to the released capability.
- **PS-LEGAL-009:** Messaging shall not pilot before counsel-reviewed Terms,
  Privacy, retention/deletion, consent, moderation, abuse, notification, and
  lawful-request handling are operational.
- **PS-LEGAL-010:** Public/permissioned Journal shall not release before exact
  audience preview, revocation, block/report/contact, indexing/search behavior,
  AI grounding effects, minors/age position, and public-content terms are
  reviewed.
- **PS-LEGAL-011:** Multimodal private AI shall not pilot before provider/data-
  flow, upload/OCR, prompt-injection, retention, deletion, confidentiality,
  consequential-use, and sensitive-data review.
- **PS-LEGAL-012:** Qualification Alignment shall disclose that it analyzes
  member-supplied criteria and history, not hiring probability, legal
  qualification, automated application, or employer decision.
- **PS-LEGAL-013:** The product shall define an age/minors position and enforce
  required restrictions before broad registration; it shall not infer consent
  from mere use.
- **PS-LEGAL-014:** Accessibility claims shall be evidence-backed and include a
  contact/remediation path; internal WCAG intent alone is not a conformance
  claim.
- **PS-LEGAL-015:** Marketing/homepage copy shall match live capability,
  privacy, AI, verification, audience, persistence, and security behavior.
- **PS-LEGAL-016:** “Private,” “secure,” “verified,” “encrypted,” “anonymous,”
  “deleted,” “AI will not train,” and similar claims require exact technical/
  contractual support and scoped language.
- **PS-LEGAL-017:** Maintain a current subprocessor/vendor register with data
  class, region, purpose, contract/DPA status, retention, model-training/data-
  use terms, security evidence, incident process, and exit/deletion plan.
- **PS-LEGAL-018:** Production access roles, support access, moderation access,
  break-glass behavior, audit, secrets, and incident response shall be defined
  before personnel can inspect member content.
- **PS-LEGAL-019:** Establish privacy-request intake and identity verification
  for access, correction, export, deletion, objection/restriction, and appeals as
  applicable; do not expose another person's data during verification.
- **PS-LEGAL-020:** Define deletion semantics for active stores, derived data,
  indexes, caches, backups, providers, exports, projections, messages,
  moderation/legal holds, and recipient copies. UI shall not overpromise.
- **PS-LEGAL-021:** Define security incident detection, severity, containment,
  evidence, provider coordination, member/regulator notice assessment, and
  post-incident correction.
- **PS-LEGAL-022:** Define retention schedules and deletion jobs before
  collecting a data class; “keep everything indefinitely for future AI” is not
  acceptable.
- **PS-LEGAL-023:** Public AI and profile features require abuse/rate-limit,
  impersonation, sensitive-source, owner-disable, source-correction, and
  contact/escalation controls.
- **PS-LEGAL-024:** Any employment, education, health, financial, or other
  consequential-use expansion requires a separate legal/fairness/product review
  and may not inherit approval from journaling features.
- **PS-LEGAL-025:** Telemetry shall be data-minimized, purpose-bound, retention-
  limited, access-controlled, and separated from member content.
- **PS-LEGAL-026:** Test fixtures, screenshots, support artifacts, and review
  evidence shall use synthetic/redacted data unless the member explicitly
  authorizes a controlled real-data validation.
- **PS-LEGAL-027:** The release record shall name open legal/security items and
  shall not label them passed because documentation exists.
- **PS-LEGAL-028:** Counsel advice and security findings shall be translated into
  versioned requirements without committing privileged or sensitive details to
  a public repository.
- **PS-LEGAL-029:** Policy/version changes shall have effective dates,
  member-notice/consent rules where needed, and production configuration proof.
- **PS-LEGAL-030:** Broad launch requires an owner-signed readiness record
  separating internal checklist, counsel review, security assessment,
  operational readiness, deployment, and live verification.

## Stage gates

### Gate L0 — Start now

- data-flow and vendor inventory;
- actual public footer/contact/policy audit;
- retention/deletion matrix;
- AI/voice/upload/message/public-content claim inventory;
- owner for privacy requests, security incidents, moderation, and support;
- open-counsel-question register.

### Gate L1 — Before closed multi-member Journal pilot

- account/identity/privacy/export/delete behavior documented and tested;
- real Terms/Privacy/support/accessibility/contact links appropriate to pilot;
- vendor/provider terms and secure configuration reviewed;
- incident and privacy-request operating path exercised.

### Gate L2 — Before public/permissioned Journal

- counsel review of public content, audience/share, indexing, revocation,
  takedown, copyright/impersonation, age, and AI grounding;
- security/threat-model and payload-isolation pass;
- moderation/contact operations and exact-audience member validation.

### Gate L3 — Before private multimodal Ask Slate

- upload/OCR/malware/injection/confidentiality/provider/retention/deletion
  review;
- consequential-use and source/citation/error disclosures;
- secure deletion and provider failure verification.

### Gate L4 — Before messaging

- counsel-reviewed consent, acceptable use, retention/deletion, moderation,
  evidence/legal hold, notifications, safety, minors/age, and abuse response;
- threat model and operational moderation/on-call proof.

### Gate L5 — Before broad launch

- counsel and security review dispositions;
- policy/site parity and vendor register current;
- privacy request, deletion, moderation, support, incident, accessibility, and
  backup/restore exercises;
- owner approval with exact remaining risk.

## Relationship to professional readiness gates

`PS-OPS-001` Gate Launch consumes the applicable L0-L5 result; it does not
replace or approve it. Legal and counsel evidence remains owned by this
standard, security assessment remains an actual reviewer result, and repository
drafting remains neither legal advice nor approval.

When the exact release, audience, reviewers, date, evidence, and result match,
one `PROFESSIONAL_READINESS_EVIDENCE.md` record may carry both the applicable
L-gate and Gate Launch rows. Record each result separately inside that one
record rather than running duplicate ceremonies.

## Required release evidence

Every affected package links to this standard and records: applicable gate,
reviewer, date, evidence location, exact passed/conditional/failed items,
production configuration, unresolved risks, and re-review trigger.

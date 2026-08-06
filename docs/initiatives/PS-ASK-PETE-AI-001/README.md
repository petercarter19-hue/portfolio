# PS-ASK-PETE-AI-001 — Public Ask Pete AI

## Activated refinement direction — 2026-08-06

Pete accepted a recruiter-first Ask Pete refinement and directed normal
parallel branch development rather than waiting for unrelated site work.
Ask Pete is the first reference consumer of PS-DATA-FOUNDATION-001.

The flagship interaction is a concise recruiter brief that:

1. explains Pete's professional through-line;
2. surfaces consequential claims rather than merely listing roles;
3. attaches each supported claim to an inspectable exact source version/span;
4. separates evidence, interpretation, partial support, and what is not
   established publicly;
5. proposes thoughtful human interview questions; and
6. offers a private Ask Pete directly path when approved public information is
   insufficient.

The current backend candidate now adds the explicit public-source manifest,
deterministic resume adapter, structured grounded-answer service, recruiter
quality contract, privacy-safe diagnostics, and a default-off `POST /api/chat`
integration seam. It does not change the resume page, provider configuration,
schema, or production behavior. The new path remains disabled unless a later
release decision explicitly enables `PEERSLATE_ASK_PETE_GROUNDED_ENABLED`.
Material resume-page visual implementation remains tied to Pete's accepted
warm recruiter-evidence direction, ChatGPT-created visual authority, and later
code-level accessibility and contrast verification.

## Package status

- Status: **Backend candidate implemented on its isolated branch; not yet
  merged, deployed, enabled, or live**
- Product name: **Ask Pete AI**
- Audience: Logged-out/public visitors using approved public Pete sources only
- Current manager/writer: Codex on the recorded isolated backend lane
- Private member intelligence: `PS-ASK-SLATE-AI-001`, not this package
- Runtime effect while the new flag is false: None; the legacy JSON response
  remains unchanged

## Current backend candidate

- `data/ai_sources/ask_pete_public_v1.json` is the explicit AI-use allowlist.
  Public resume visibility alone does not grant AI use.
- `services/ask_pete/manifest.py` renders only approved fields from the
  structured public resume and requires every rendered record to match its
  approved SHA-256 content digest.
- `services/ask_pete/service.py` applies the shared provider-neutral request,
  source authorization, execution limit, citation, support-state, and trace
  contracts from `services/ai_foundation/`.
- `services/ask_pete/response.py` returns claim-level support labels, exact
  citation spans, openable resume locators, visible limitations, follow-up
  questions, and an honest contact handoff.
- The current contact handoff opens Pete's existing contact options. It does
  not falsely claim that on-platform private messaging, notification, or
  knowledge-base updating is live.
- The legacy `docs/knowledge/*.md` bundle is not silently included in the new
  recruiter source set.
- The first implementation is data-driven: Pete's name and profile slug come
  from the manifest, not shared backend logic, preserving the future
  Ask-[Name] pattern.

The exact backend-to-visual contract is recorded in
`02_BACKEND_CONTRACT_AND_VISUAL_HANDOFF.md`.

## Current owner decision

Ask Pete AI remains the public Pete-specific assistant. It is the current
instance of the future audience-authorized **Ask [Name] AI** pattern. It must
not grow into the private signed-in assistant merely because infrastructure is
shared.

The signed-in intelligence umbrella is **Ask Slate AI**; **Ask My Slate** is
its owner action. Private voice, document, screenshot/OCR, job-description,
Qualification Alignment, and owner-history exploration move to
`PS-ASK-SLATE-AI-001`. This supersedes the earlier plan to put public and
private multimodal work under one Ask Pete docket.

## Honest current production baseline

Today:

- a public browser sends one typed message to `POST /api/chat`;
- the server uses a bounded set of approved public Pete knowledge sources;
- answers are public-profile responses for visitors;
- no voice input, attachment/OCR, private member retrieval, saved target,
  signed-in Ask Slate workspace, or private Qualification Alignment is proven
  by this endpoint; and
- no public route or model may infer access to Pete's or another member's
  private Journal.

## Required public boundary

1. Retrieve only records whose current exact version is public-authorized for
   the actual visitor.
2. Never fetch a private Journal and filter it in application/UI after retrieval.
3. Show public-safe sources and distinguish fact, inference, uncertainty, and
   missing information.
4. Defend against prompt injection, scraping/abuse, impersonation, source
   poisoning, and private-source leakage.
5. Provide owner disable/correction and public contact/report paths before the
   reusable Ask [Name] pattern expands.
6. Do not edit, save, publish, send, connect, apply, or change an audience.
7. Treat any public homepage representation as a downstream projection of the
   real accepted product under the Visual Integrity Standard.

## Future public refinement questions

`01_DISCOVERY_AGENDA.md` now covers only public Ask Pete/Ask [Name] behavior.
Private multimodal and member-history decisions are controlled by the Ask Slate
package.

## Exclusions

- No private Ask Slate mode; “Owner AI” remains an internal authorization term,
  not a public Ask Pete capability or user-facing assistant.
- No private uploads, OCR, job-posting analysis, or Qualification Alignment.
- No cold outreach, application, public job listing, or hiring probability.
- No automatic content/profile/publication change.
- No visual implementation, provider-setting change, production enablement,
  deployment, or private-message persistence is authorized by this backend
  candidate.

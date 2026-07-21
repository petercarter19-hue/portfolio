# PS-ASK-PETE-AI-001 — Public Ask Pete AI

## Package status

- Status: **Public typed assistant live; future public refinement planned, not
  active**
- Product name: **Ask Pete AI**
- Audience: Logged-out/public visitors using approved public Pete sources only
- Future manager/writer: Unassigned
- Private member intelligence: `PS-ASK-SLATE-AI-001`, not this package
- Runtime effect of this governance update: None

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
- No implementation branch or runtime expansion is authorized here.

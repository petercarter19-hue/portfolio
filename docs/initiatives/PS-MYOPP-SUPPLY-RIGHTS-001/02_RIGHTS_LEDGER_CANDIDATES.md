# 02 — Rights-ledger candidates

## Status vocabulary

Each cell below is deliberately a legal/operational disposition, not a
prediction.  It is evaluated against the exact provider, region, product,
surface, and contract eventually selected.

| Mark | Meaning |
|---|---|
| **E** | The cited public source expressly addresses this narrow point.  It is not a PeerSlate approval. |
| **U** | Explicitly unverified: the reviewed official-public source does not expressly grant or settle the right. |
| **C** | Contract and qualified-counsel decision required.  The runtime default is deny until the decision is recorded. |
| **D** | Do not use this right at all under the current evidence. |

Every `U/C` cell means `source_policy` must deny the action at registration and
point of use.  “AI/ML use” includes prompts, embeddings, training,
fine-tuning, evaluation corpora, and other transformations; none is presumed.
“Survivable minimal facts” includes every source-derived title, employer,
identifier, date, hash, URL, or attribution value — not just the body.

## Candidate source-policy record

Each later source registration supplies a versioned record with:

```text
source_id, source_class, provider, product, territory, agreement_version,
policy_version, effective_at, evidence_urls[], allowed_surfaces[],
claim_allowlist[], reproduction_right, summary_right,
display, excerpt, full_description, storage, ai_ml_use, caching, retention,
attribution, removal, termination, exit, survivable_minimal_facts,
closure_change_signals, review_due_at, counsel_signoff_ref, owner_decision_ref
```

Every rights value must identify permitted fields, audience/surface, limits,
expiry, and evidence.  A blank, expired, contradictory, or `U/C` field is a
denial, not an implicit allow.  The rights evaluator is also passed the source
version, action, target surface, and current time; it returns a reason code
that can be shown truthfully without exposing protected provider material.
For company context, `claim_allowlist`, `reproduction_right`, and
`summary_right` are independently enforced at registration and point of use;
they do not inherit permission from display or API availability.

## Commercial candidate A — Adzuna API

Official terms allow an API user to publish listings subject to specified
labelling, say other organisational uses after a limited trial need written
consent and may need a licence, and require removal of acquired data from web
pages on termination.  They do not turn this package into an API user or
resolve all rights.  Source: [Adzuna API Terms](https://developer.adzuna.com/docs/terms_of_service)
(accessed 2026-08-24).

| Right | Candidate disposition |
|---|---|
| Display | **E/C** — terms address publishing adverts for an API user; no PeerSlate user/licence exists, so registration remains denied pending executed terms. |
| Excerpt | **U/C** — no public excerpt length, field, or surface rule located. |
| Full description | **U/C** — publishing adverts is not a precise full-description storage/render grant. |
| Storage | **U/C** — no backend persistence allowance or prohibition located. |
| AI/ML use | **U/C/D** — no AI, prompt, embedding, training, or transformation permission located; deny. |
| Caching | **U/C** — no cache/index horizon located. |
| Retention | **U/C** — no ordinary retention period located. |
| Attribution | **E** — published advert label, logo/link, and dimensional requirements are stated; exact current branding/territory must be contract-checked. |
| Removal | **U/C** — no public takedown response window located. |
| Termination | **E/C** — the terms require immediate removal of acquired data from website pages; counsel must determine backend, cache, log, and index consequences. |
| Exit | **U/C** — no export/portability or migration right located. |
| Survivable minimal facts | **U/C/D** — no survival grant; source facts remain deny-by-default after removal/termination. |

## Commercial candidate B — Jooble REST API

Jooble's public API page describes posting query results in an integrator's
design and its connection guide requires a regional key and compliance with
API terms.  The public site terms reserve IP, restrict republication, and say
third-party networks have their own terms.  The actual API terms were not
available in the reviewed public material.  Sources: [API page](https://jooble.org/api/about),
[connection guide](https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api),
and [site terms](https://jooble.org/info/terms) (all accessed 2026-08-24).

| Right | Candidate disposition |
|---|---|
| Display | **E/U/C** — the API page describes posting results, but applicable API terms and exact fields are unverified; deny pending executed licence. |
| Excerpt | **U/C** — a sample response contains a snippet; no general excerpt entitlement/limit was found. |
| Full description | **U/C** — not expressly granted. |
| Storage | **U/C** — not expressly granted. |
| AI/ML use | **U/C/D** — no AI/ML permission located; deny. |
| Caching | **U/C** — not expressly granted. |
| Retention | **U/C** — not expressly granted. |
| Attribution | **U/C** — no applicable API attribution rule was publicly available. |
| Removal | **U/C** — site terms describe takedown/removal discretion, not an integrator removal obligation. |
| Termination | **U/C** — no applicable API termination data disposition located. |
| Exit | **U/C** — no export/portability right located. |
| Survivable minimal facts | **U/C/D** — third-party listing content and source metadata do not survive by assumption. |

## Permitted-public candidate — USAJOBS API

USAJOBS public-job search documentation incorporates API terms that limit API
data to the identified requesting company and require prior written approval
for other uses; it also prohibits creating derivative works from API services
and data.  This makes the source a formal approval/counsel gate, not an
unrestricted public-data fallback.  Source: [USAJOBS rate-limit and API terms](https://developer.usajobs.gov/guides/rate-limiting)
(accessed 2026-08-24).

| Right | Candidate disposition |
|---|---|
| Display | **C/D** — written approval for the exact PeerSlate use is required; no implied publication right. |
| Excerpt | **C/D** — no excerpt permission found. |
| Full description | **C/D** — no full-description permission found. |
| Storage | **C/D** — no persistence allowance found. |
| AI/ML use | **C/D** — derivative-work restriction makes counsel confirmation mandatory; deny. |
| Caching | **C/D** — no cache/index permission found. |
| Retention | **C/D** — no retention rule for PeerSlate found. |
| Attribution | **U/C** — no applicable attribution form found. |
| Removal | **U/C** — no integrator takedown window found. |
| Termination | **U/C** — API modification/discontinuance language is not a data disposition plan. |
| Exit | **U/C** — no export/portability right found. |
| Survivable minimal facts | **C/D** — no survival right; keep only PeerSlate-owned action records absent written approval. |

## Direct employer/ATS candidates — Greenhouse and Lever

Greenhouse describes the Job Board API as exporting a customer's public jobs to
build that customer's career site; its public legal materials make customer
rights order-form/contract dependent.  Lever's public posting documentation is
for a company's job site, and Lever's terms give contracted customers a
non-transferable, internal-use service right.  Neither public source grants a
third-party cross-employer discovery product its desired rights.  Sources:
[Greenhouse API overview](https://support.greenhouse.io/hc/en-us/articles/10568627186203-Greenhouse-API-overview),
[Greenhouse legal center](https://www.greenhouse.com/legal),
[Lever Postings API](https://github.com/lever/postings-api/blob/master/README.md),
and [Lever terms](https://www.lever.co/legal/terms-of-service?hsLang=en-us)
(all accessed 2026-08-24).

| Right | Greenhouse candidate | Lever candidate |
|---|---|---|
| Display | **U/C/D** — custom employer career-site purpose, not third-party discovery. | **U/C/D** — company-site purpose and company-domain context, not third-party discovery. |
| Excerpt | **U/C** | **U/C** |
| Full description | **U/C** | **U/C** |
| Storage | **U/C** | **U/C** |
| AI/ML use | **U/C/D** | **U/C/D** |
| Caching | **U/C** | **U/C** |
| Retention | **U/C** | **U/C** |
| Attribution | **U/C** — employer/provider instruction required. | **U/C** — employer/provider instruction required. |
| Removal | **U/C** — no third-party response obligation found. | **U/C** — no third-party response obligation found. |
| Termination | **U/C** — order-form and employer terms decide. | **U/C** — agreement and employer terms decide. |
| Exit | **U/C** | **U/C** |
| Survivable minimal facts | **U/C/D** | **U/C/D** |

## Official employer-owned source candidate — Microsoft Careers

This is a source-class evidence candidate, not a Microsoft selection or a
general employer-content licence.  Microsoft Careers describes its career-site
features and job-view experience, making it an official employer-owned source
from which a later policy could identify an attributable employer fact or a
labelled employer-stated claim.  Microsoft’s public terms state that the
services are personal/non-commercial unless otherwise specified, reserve
ungranted rights, and prohibit ungranted copying/distribution.  Neither page
grants PeerSlate a general right to reuse employer content.  Sources:
[Microsoft Careers transparency FAQ](https://careers.microsoft.com/v2/global/en/transparency.html)
and [Microsoft Terms of Use](https://www.microsoft.com/en-us/legal/terms-of-use)
(accessed 2026-08-24).

| Right | Candidate disposition |
|---|---|
| Claim allowlist | **C1 policy / U/C** — may contain only `official_identity`, `official_location`, and visibly labelled `employer_stated_claim` types named in the policy; the exact source/field subset remains denied until rights are recorded. |
| Display | **U/C/D** — no PeerSlate display grant located. |
| Excerpt | **U/C/D** — no excerpt length or reuse grant located. |
| Full description | **U/C/D** — no right to reproduce career-site/job or employer narrative content. |
| Storage | **U/C** — no backend persistence right located. |
| AI/ML use | **U/C/D** — no prompt, embedding, training, evaluation, or transformation right located; deny. |
| Caching | **U/C/D** — no cache/index permission located. |
| Retention | **U/C** — no retention rule for PeerSlate located. |
| Attribution | **U/C** — C1 requires source-link attribution, but no applicable source attribution grant/form was located. |
| Removal | **U/C** — no PeerSlate takedown response obligation or path located. |
| Termination | **U/C** — no integrator termination/data-disposition term located. |
| Exit | **U/C** — no export or migration right located. |
| Survivable minimal facts | **U/C/D** — no survival entitlement; retain only PeerSlate-owned action/member records unless an exact later policy permits source facts. |

## Narrow company-fact candidate — SEC EDGAR

SEC documents no-key access to filing/submission and XBRL JSON data, plus fair
access limits.  It does not supply this package with a general reproduction or
company-intelligence licence.  Sources: [EDGAR APIs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
and [SEC developer resources](https://www.sec.gov/about/developer-resources)
(accessed 2026-08-24).

| Right | Candidate disposition |
|---|---|
| Display | **U/C** — may be considered only for a narrow, attributed factual claim after source/right review. |
| Excerpt | **U/C** — do not reproduce issuer narrative by assumption. |
| Full description | **U/C/D** — do not render filing narrative as company context. |
| Storage | **U/C** — source-specific and purpose-bounded; no unlimited store inferred. |
| AI/ML use | **U/C/D** — no AI/ML permission inferred. |
| Caching | **U/C** — fair-access guidance is not a caching licence. |
| Retention | **U/C** — no retention entitlement inferred. |
| Attribution | **U/C** — product policy requires exact source/filing citation even though a prescribed attribution form was not found. |
| Removal | **U/C** — correction/restatement and source-policy handling need a later rule. |
| Termination | **U/C** — no provider termination data disposition applies; rights for source-derived facts still require review. |
| Exit | **U/C** — no PeerSlate migration/export entitlement inferred. |
| Survivable minimal facts | **U/C/D** — preserve only PeerSlate action records unless the later source policy affirmatively permits facts. |

## Termination rehearsal invariant

No C11/C12 candidate passes if its `source_policy` cannot answer all twelve
cells and execute a reversible proof: disable registration; stop acquire;
remove/withhold all prohibited bodies and projections; re-evaluate every
point-of-use action; retain only permitted source facts plus PeerSlate-owned
action/member records; and produce a content-free audit of the disposition.
The proof is contractual/operational validation, not a claim that C1 has
performed it.

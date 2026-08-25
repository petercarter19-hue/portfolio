# 01 — Provider and source-class comparison

## Reading rule

This is a bounded evidence comparison, not a procurement shortlist, provider
selection, or instruction to create an account.  “Public”, “API”, “JSON”, and
“can display” describe only what the cited provider page says.  They do not
establish PeerSlate's rights to store, transform, cache, retain, or use content
with AI.

All external sources in this document were accessed on **2026-08-24**.  The
full source ledger and every operational-right disposition are in
[05_CITATIONS_AND_OWNER_DECISIONS.md](05_CITATIONS_AND_OWNER_DECISIONS.md) and
[02_RIGHTS_LEDGER_CANDIDATES.md](02_RIGHTS_LEDGER_CANDIDATES.md).

## Representative classes

| Source class / representative | Official-public evidence | What is established now | What is not established now |
|---|---|---|---|
| Licensed commercial aggregate — **Adzuna API** | [Terms](https://developer.adzuna.com/docs/terms_of_service) describe conditional publishing, attribution, trial limits, written-consent/licence conditions, and web-page removal at termination. | It is an example where public terms discuss advertisement publication and attribution. | PeerSlate has no API account or licence; storage, AI/ML, cache/index, backend deletion, exit, and minimal-fact survival are not expressly granted. |
| Licensed commercial aggregate — **Jooble REST API** | [API page](https://jooble.org/api/about) says results may be posted in an integrator's design; [connection guide](https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api) requires a regional key and API terms; [site terms](https://jooble.org/info/terms) reserve IP and prohibit copying for republication without express permission. | A second commercial candidate has a public integration interface and a visible rights ambiguity. | The public material does not provide the API terms or an executed licence that resolves PeerSlate display, persistence, AI, removal, termination, or exit. |
| Permitted public announcement API — **USAJOBS** | [API guide](https://developer.usajobs.gov/guides/rate-limiting) exposes public-job search limits and incorporates API terms.  Those terms restrict API data to the requesting company and say other use needs written approval. | The source is public-sector and has a formal API/terms path; it is not assumed open-data job-feed permission. | A PeerSlate use case, display, derivative/AI treatment, retention, and redistribution authority require written approval and counsel review. |
| Direct employer/ATS publication — **Greenhouse Job Board API** | [Official support](https://support.greenhouse.io/hc/en-us/articles/10568627186203-Greenhouse-API-overview) says the API exports a customer's public job-board/job-post information to build that customer's career site; [legal center](https://www.greenhouse.com/legal) ties service rights to customer agreements and order forms. | The interface is evidence of an employer-facing publication path, not a cross-employer marketplace licence. | Third-party discovery, reuse, storage, AI, caching, removal, termination, and exit rights are not granted by the public API overview. |
| Direct employer/ATS publication — **Lever Postings API** | [Official Lever repository](https://github.com/lever/postings-api/blob/master/README.md) says the API is for a company job site, limits CORS to company domains, and exposes published postings; [Lever terms](https://www.lever.co/legal/terms-of-service?hsLang=en-us) make contracted service access internal, non-transferable, and non-sublicensable. | It is a direct-employer publication interface with a clear employer-domain context. | It does not grant a third-party aggregate/discovery licence or settle any rights cell. |
| Official employer-owned source — **Microsoft Careers** | [Microsoft Careers transparency FAQ](https://careers.microsoft.com/v2/global/en/transparency.html) is an official employer career-site page; [Microsoft Terms of Use](https://www.microsoft.com/en-us/legal/terms-of-use) reserve content rights and prohibit ungranted commercial copying/distribution. | It is evidence of a source from which a narrowly attributable employer fact or visibly labelled employer-stated claim could be evaluated. | It does not supply a general employer-content, reproduction, summary, storage, or AI licence.  Every source-specific rights cell remains `U/C` and fail-closed. |
| Source-linked company facts — **SEC EDGAR / data.sec.gov** | [SEC API documentation](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) describes no-key JSON access to submissions and XBRL facts; [developer guidance](https://www.sec.gov/about/developer-resources) requires efficient, fair access. | This is a narrow, official source for attributable filing facts and `as_of` dates. | It is not a licence to reproduce issuer narrative, make reputation claims, cache without limit, or synthesize company judgments.  Issuer and other third-party rights remain relevant. |

## Parent document 05 §10 evaluation matrix

This mandatory per-candidate matrix records public evidence, not a score or a
procurement recommendation.  **E** means the linked official-public material
addresses the narrow point; it is never a PeerSlate grant.  **U** means public
evidence was not found or does not settle the point.  **C** means contract and
qualified-counsel review are required.  **D** is the current deny-at-use
disposition.  “Unknown/Public evidence absent” is intentional: no account,
trial, pricing request, provider contact, or API call was made to fill it.

| Criterion | Adzuna | Jooble | USAJOBS | Greenhouse | Lever | SEC / company-context | Employer-owned source |
|---|---|---|---|---|---|---|---|
| Coverage | **E/C** — API adverts; territory/source completeness unverified in [terms](https://developer.adzuna.com/docs/terms_of_service). | **E/U/C** — result posting is described in the [API page](https://jooble.org/api/about); coverage guarantee absent. | **E/U** — public announcements endpoint, not a coverage guarantee, in the [API guide](https://developer.usajobs.gov/guides/rate-limiting). | **E/U** — one customer's public board, not market coverage, in [support docs](https://support.greenhouse.io/hc/en-us/articles/10568627186203-Greenhouse-API-overview). | **E/U** — one company's published postings, not market coverage, in the [Postings API](https://github.com/lever/postings-api/blob/master/README.md). | **E/U** — SEC filings/structured data, not job coverage, in [EDGAR docs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces). | **E/U** — one employer's published page; no cross-employer coverage. |
| Identifier stability | **U/C** — no public stability commitment. | **U/C** — no public stability commitment. | **U/C** — no public stability commitment for PeerSlate use. | **U/C** — no cross-employer stability commitment. | **U/C** — no cross-employer stability commitment. | **U/C** — identifiers are documented data, but a PeerSlate retention/stability right is not. | **U/C** — source-specific only; no stability commitment. |
| Update / closure latency | **U/C** — no public SLA for change/closure. | **U/C** — no public SLA for change/closure. | **U/C** — guide is not a closure-latency SLA. | **U/C** — no third-party change/closure SLA. | **U/C** — no third-party change/closure SLA. | **E/U/C** — [SEC docs](https://www.sec.gov/search-filings/edgar-application-programming-interfaces) describe prompt JSON updates, not correction/claim-removal latency. | **U/C** — no reusable change/closure SLA. |
| Duplicate rates | **Unknown/Public evidence absent.** | **Unknown/Public evidence absent.** | **Unknown/Public evidence absent.** | **Unknown/Public evidence absent.** | **Unknown/Public evidence absent.** | **Unknown/Public evidence absent; not an opportunity feed.** | **Unknown/Public evidence absent; not a feed.** |
| Field completeness | **U/C** — no contract-level completeness promise. | **E/U/C** — [connection guide](https://help.jooble.org/en/support/solutions/articles/60000922689-how-to-connect-to-the-jooble-rest-api) shows fields, not completeness. | **U/C** — documented endpoint is not a completeness promise. | **U/C** — employer board export purpose, no marketplace completeness promise. | **U/C** — published posting fields, no completeness promise. | **E/U/C** — submissions/XBRL fields are documented; issuer/context completeness is not. | **U/C** — each employer source and claim field must be approved separately. |
| Display / full-description rights | **E/C** — conditional publication/attribution only; no PeerSlate agreement. | **E/U/C** — result posting is described; applicable API terms unavailable publicly. | **C/D** — requester-specific terms and written approval gate. | **U/C/D** — customer career-site purpose only. | **U/C/D** — company-site purpose only. | **U/C/D** — C1 permits only structured facts if policy rights allow; no narrative reproduction. | **U/C/D** — no generic page/job/employer-content reuse right. |
| AI transformation | **U/C/D** — public terms do not grant it. | **U/C/D** — public evidence does not grant it. | **C/D** — derivative-work restriction requires approval/counsel. | **U/C/D** — no third-party AI right. | **U/C/D** — no third-party AI right. | **U/C/D** — no AI transformation inferred from access. | **U/C/D** — no AI transformation grant. |
| Caching / retention | **U/C** — no backend/cache horizon. | **U/C** — no applicable API horizon public. | **C/D** — no PeerSlate persistence permission. | **U/C** — customer agreement/provider terms control. | **U/C** — employer/provider agreement controls. | **U/C** — fair access is not caching/retention permission. | **U/C/D** — no cache/retention right. |
| Attribution | **E/C** — public terms prescribe conditions; exact contract/territory remains required. | **U/C** — applicable API attribution absent publicly. | **U/C** — exact applicable form unverified. | **U/C** — employer/provider instruction required. | **U/C** — employer/provider instruction required. | **U/C** — C1 requires source attribution; no source grant/form inferred. | **U/C** — C1 requires source link; source grant/form absent. |
| Removal | **E/U/C** — termination page removal is stated; ordinary takedown details unverified. | **U/C** — site discretion is not an integrator SLA. | **U/C** — no relevant takedown SLA. | **U/C** — no third-party obligation public. | **U/C** — no third-party obligation public. | **U/C** — correction/restatement handling needs policy. | **U/C** — no integrator removal path. |
| Rate limits | **E/U/C** — public trial/API conditions exist; production limits contract-gated. | **U/C** — key/terms required; no reviewed production limit. | **E/C** — [official guide](https://developer.usajobs.gov/guides/rate-limiting) publishes limits/terms; use remains approval-gated. | **U/C** — no third-party production limit. | **U/C** — no third-party production limit. | **E/C** — [SEC guidance](https://www.sec.gov/about/developer-resources) sets fair-access expectations; not a right to operate. | **U/C/D** — no permitted programmatic access assumed. |
| Reliability | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** | **Unknown/Public SLA absent.** |
| Privacy posture | **U/C** — no PeerSlate data-processing posture established. | **U/C** — no PeerSlate data-processing posture established. | **U/C** — public-system terms do not settle PeerSlate processing. | **U/C** — DPA/order-form review required. | **U/C** — contract/employer flow review required. | **U/C** — source access does not settle issuer/member-data processing. | **U/C/D** — no member data may be supplied; rights/privacy review needed. |
| Cost per useful live opportunity | **Unknown/Public evidence absent; contract/pricing required.** | **Unknown/Public evidence absent; contract/pricing required.** | **Unknown/Public evidence absent; approval/use fit required.** | **Unknown/Public evidence absent; employer/provider contract required.** | **Unknown/Public evidence absent; employer/provider contract required.** | **Not comparable; not an opportunity feed.** | **Not comparable; not an opportunity feed.** |
| Exit / migration | **U/C** — no export/portability right. | **U/C** — no export/portability right. | **U/C** — no PeerSlate exit right. | **U/C** — customer/employer agreement decides. | **U/C** — customer/employer agreement decides. | **U/C** — no PeerSlate migration entitlement inferred. | **U/C** — no migration entitlement. |
| Minimal-metadata retention compatibility | **U/C/D** — no survival grant. | **U/C/D** — no survival grant. | **C/D** — retain only PeerSlate-owned records absent approval. | **U/C/D** — no survival grant. | **U/C/D** — no survival grant. | **U/C/D** — C1 structured-fact class still needs exact survival permission. | **U/C/D** — no survival grant for employer facts/statements. |

## C1 comparison conclusions

1. **No class is selected.** Adzuna and Jooble remain representative commercial
   candidates only; the package has not contacted them, created an account,
   started a trial, requested pricing, or agreed to terms.
2. **Commercial feeds need executed rights.** Adzuna's public terms are the
   strongest visible example of conditions, but they still leave material
   rights unknown.  Jooble's public API and site terms demonstrate why an API
   page and a site licence must be read together and still may not substitute
   for API-specific terms.
3. **“Public” does not erase the gate.** USAJOBS calls for written approval
   beyond the requester-specific API purpose; Greenhouse and Lever describe
   employer/customer career-site contexts; SEC access rules govern retrieval,
   not a general content licence.
4. **Company facts are a distinct class.** C1 fixes the allowed class/claim
   boundary: an employer source can support only attributable identity/location
   facts or visibly labelled employer-stated claims; registry/SEC can support
   only enumerated identity, filing metadata, and structured filing facts; and
   a licensed-data source starts with no allowed claim.  Exact source policy
   rights still gate every display, reproduction, summary, retention, and AI
   action.  No class may become a company score, culture conclusion, hiring
   prediction, or a summary that outruns its sources.
5. **The launch gate is unchanged.** The parent requirement for an
   owner-approved licensed commercial opportunity feed before a Level 3
   private-sector operation remains in force.  C1 has prepared the comparison
   and guardrails; it has not met that release gate.

## Required later selection packet

Before C11 is activated, the manager returns one provider-specific packet to
Pete and counsel containing the executed terms/order form, exact territories
and fields, every ledger value, a removal/termination/exit runbook, the source
of truth for change/closure signals, permitted AI uses, member-facing
attribution, retention/cache/index limits, and a testable minimal-fact
survival decision.  An API key, test response, commercial conversation, or
public documentation alone fails this admission packet.

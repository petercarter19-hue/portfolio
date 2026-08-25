# 04 — Private import and company-context policy

## Private member imports are a different system

Member-provided pasted text and documents use the future owner-scoped
`member_import` path, not the shared connector path.  A member import:

- is private to the server-derived `user_key` before any read, extraction,
  rendering, AI use, export, correction, or deletion;
- is sanitized/extracted deterministically from untrusted input with explicit
  outcomes; an AI system is never the extraction authority;
- is individually deletable and subject to both the member lifecycle and any
  applicable content-rights obligation at point of use; and
- may support that member's private Qualification Alignment only.

It must **never** become a `source_receipt`, `source_listing`, canonical
opportunity, shared recommendation/listing, cross-member result, shared
discovery-index input, or company-context input.  This is an absolute isolation
rule, not a later product preference.  A member supplying text does not turn
third-party content into shared inventory or erase its underlying rights.

## URL fetching remains disabled and separate

Paste and upload are permanent C10 paths.  Remote member-URL fetching is the
optional later C13 decision, not part of C1 or C10.  If Pete ever separately
authorizes C13, it must use the accepted outbound-safety and private-import
boundary: HTTPS only, per-connection address validation, redirect/size/time
budgets, no forwarded member or PeerSlate credentials, sanitation before
rendering, truthful failures, and no promotion to shared source objects.
Until then the product response is `url_fetch_unavailable` with paste/upload
alternatives, not a silent attempted fetch.

## Source-linked company context

Company context is a non-essential, optional decision aid.  The only permitted
record shape is:

```text
company_context_claim = {
  claim_text, claim_class, source_reference, source_policy_version,
  source_as_of, retrieved_at, attribution, limitation_label
}
```

### Binding C1 source-class and claim decision

This is the C1 owner-delegated policy decision required by parent document 06;
it is not a later C12 choice.  Every allowed claim must carry exact source,
`as_of`, attribution, and the policy version that permitted the claim.  A
`source_policy` must also name its exact `claim_allowlist` and separately
permit or deny reproduction and summary (including allowed fields, length,
surface, and transformation limits).  A blank or incomplete value denies the
claim.

| Source class | C1-permitted claim types only | C1 prohibitions and policy condition |
|---|---|---|
| Official employer-owned source | `official_identity` (employer name/domain as stated), `official_location` (headquarters or office location as stated), and `employer_stated_claim` limited to an explicitly sourced mission, benefit, accessibility/candidate-process, or workplace-program statement. | Facts must be attributable and source-linked; every statement must be visibly labelled **“Employer-stated”**.  No independent verification, reputation/culture conclusion, ranking, prediction, or claim outside the exact allowlist.  The exact source policy must expressly settle display, reproduction, and summary rights before use. |
| Official registry or SEC source | `registry_identity` (official entity/issuer identifier, legal name, jurisdiction or status where the source supplies it); `filing_metadata` (form/filing type, accession or filing identifier, filed/accepted date-time, reporting period, document/data URL); and `structured_filing_fact` (named XBRL or other structured field, value, unit, and period). | Every fact must retain its exact source and `as_of`.  Do not reproduce issuer/filing narrative, create a prose company summary, or synthesize a conclusion across filings or sources.  A later source policy may choose a narrower subset, never a broader claim type. |
| Licensed company-data source | This class is allowed in principle only.  Its provider-specific claim allowlist is **empty** by default. | Fail closed: no claim, display, summary, storage, AI/ML use, or survivable fact until Pete accepts the exact provider/contract packet and counsel resolves the corresponding policy cells. |

The SEC EDGAR public API is evidence of a source for filing/submission and XBRL
JSON, not permission to reproduce issuer narrative or generate analysis.  Its
published JSON access and fair-access rules are documented by the
[SEC](https://www.sec.gov/search-filings/edgar-application-programming-interfaces)
and [SEC developer guidance](https://www.sec.gov/about/developer-resources)
(accessed 2026-08-24).  An employer-owned page is likewise not a general reuse
licence: for example, [Microsoft Careers](https://careers.microsoft.com/v2/global/en/transparency.html)
is an official employer source, while [Microsoft's terms](https://www.microsoft.com/en-us/legal/terms-of-use)
reserve content rights and prohibit ungranted commercial copying (accessed
2026-08-24).  That example remains `U/C`, not a source approval.

The following are prohibited:

- sentiment, culture, reputation, controversy, or employer-quality scores;
- hiring likelihood, compensation prediction, “company fit”, or ranking;
- a claim with no source reference, no source policy, or no `as_of` date;
- resolving contradictions with a silent synthesis; and
- using any member import, criteria, assessment, save, or other member data to
  build company context.

Absent context displays **“No company context available.”** Stale context shows
its `as_of` age.  Contradictory permitted facts show both with attribution or
neither; provider absence never blocks opportunity discovery or qualification.
C12 owns the decision-gated runtime implementation, provider activation,
persistence, removal, and truthful absent-state behavior.  It may implement
only this C1 source-class/claim boundary; it does not choose or broaden it.
Later provider/contract/counsel work decides the selected provider and the
rights values for its permitted subset, including retention, correction/removal,
termination, and survivable facts.  C1 makes no live company claim.

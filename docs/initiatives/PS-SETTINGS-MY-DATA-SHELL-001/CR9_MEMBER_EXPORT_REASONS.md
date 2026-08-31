# CR9 member export reasons

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-MEMBER-REASONS-001`
**Slice:** Follow-up to C3, first of its two recorded gaps.
**Status:** Implemented. Presentation only; no route, template, flag,
schema, worker, or deployment change.

## Decision

Members reading the export screen's "not included" list were shown the
domain ledger's internal reason strings verbatim — package ids, table
names, and governance references. Accurate, but not plain language, and
against the owner's standard for member-facing copy.

This slice adds `_DOMAIN_REASONS`, a presentation-only map in
`services/account_export_experience_service.py`, following the exact
`_DOMAIN_LABELS` precedent. One plain sentence per non-included domain,
each claiming no more than the internal reason does.

## Why this survives the single-source-of-truth rule

`DOMAINS` still decides what an export contains and which category every
domain lands in; `domain_summary()` still walks `DOMAINS` itself. The map
never adds, removes, or recategorises a domain. A domain absent from the
map still renders — with the ledger's verbatim reason — so an unmapped
domain shows the truth rather than hiding it. `DOMAINS` itself was not
edited; it is another package's surface and a read-only dependency here.

## Guards

- Coverage: every current non-included domain must have a mapped sentence;
  a future domain without one fails the suite instead of shipping jargon.
- Orphans: every mapped key must still exist in `DOMAINS`.
- Fallback: a synthetic unmapped domain is proven to render the ledger's
  exact bytes.
- Jargon canary: no mapped sentence may contain a package id (either
  hyphen or underscore form), a `dbo.` table name, a `usp_` procedure
  name, a governance reference, internal vocabulary such as "allowlist"
  or "domain ledger", or any snake_case identifier.
- Drift pin: every sentence is bound by digest to the exact ledger reason
  it paraphrases, so a changed ledger reason breaks the suite and forces
  re-wording — independent review proved the original candidate lacked
  this and could silently outlive its source.

## Honest notes

- Two publication-related domains collapse to near-identical member
  sentences although their internal reasons differ (no table exists vs.
  table exists but has never been written). The distinction is
  internal-only; collapsing it for members loses nothing they could act on.
- The `projects` sentence keeps the load-bearing claim (career projects
  already exported with the living resume) and drops only the mechanism.

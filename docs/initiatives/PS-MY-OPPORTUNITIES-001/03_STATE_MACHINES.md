# 03 — State machines

Transitions not listed are illegal. Every transition records actor
(`system:<job>` | `member` | `correction`), reason code, and timestamp in the
owning object's append-only history. States are stored values, not derived
labels, except where marked *derived*.

## 1. Source listing lifecycle (`source_listing.state`) — per source only

```text
intake ──(admission checks pass)──▶ current
intake ──(admission checks fail)──▶ quarantined
quarantined ──(corrected/permitted)──▶ current
quarantined ──(rights/validity refused)──▶ invalid

current ──(new observation, different content hash)──▶ changed
current ──(source confirms closure)──▶ closed
current ──(verify attempt fails)──▶ unreachable
current ──(freshness threshold exceeded)──▶ stale

changed ──(re-verification of new version completes)──▶ current   [re-admission, §2]
changed ──(source confirms closure)──▶ closed
unreachable ──(later attempt succeeds, content unchanged)──▶ current
unreachable ──(later attempt succeeds, content differs)──▶ changed
unreachable ──(source confirms closure)──▶ closed
unreachable ──(outage exceeds closure-decision threshold)──▶ stale
stale ──(successful re-verification)──▶ current | changed
closed, invalid: terminal (append-only corrections only)
```

Rules:

- This machine is strictly **per source head**. Duplicate detection, linking,
  merge, and split are canonical-level concerns and live entirely on
  `canonical_opportunity` (§9); a listing has no `duplicate` or `merged`
  lifecycle state. Every listing is linked to exactly one canonical
  opportunity (directly or through a §9 merge tombstone) and keeps its own
  lifecycle regardless of linking changes.
- **Application-link validity is a separate persisted sub-state, not a
  lifecycle transition**: `application_link_state ∈ valid | invalid |
  unknown` with its own attempt/validation timestamps, reason, and recovery
  (doc 02 §1; doc 05 §5). A `current` listing whose link is `invalid` or
  outside its validation window fails gate condition 6 (doc 05 §6) without
  leaving `current` — link invalidity is neither closure nor outage, and a
  later successful validation restores eligibility with no lifecycle event.
- Only a **successful** verification updates
  `last_successfully_verified_at`; every attempt updates `last_attempted_at`
  (invariant 3, doc 02).
- `closed` requires source confirmation (explicit closed marker, authoritative
  410/removal per policy). An outage is never closure. The exact freshness and
  closure-decision thresholds are deferred owner decisions (doc 15 §3); the
  mechanism is not.
- `stale`, `unreachable`, `changed`, `closed`, `invalid`, and `quarantined`
  remove **that source head** from gate eligibility (doc 05 §6). Whether the
  *opportunity* leaves current results is the aggregate question §9 answers:
  it remains eligible while at least one rights-permitted `current` source
  head passes the gate. No member saved/history/Slate row is touched either
  way.

## 2. Changed-posting re-admission (REC-03, decision-pending)

Two different surfaces re-admit differently:

- **General current pool**: the *system* re-admits. When the ingestion
  pipeline verifies the new `source_version`, derives a new
  `requirement_version` **only if the normalized requirement clauses
  materially differ** (otherwise the existing one is retained — §10), and
  the Live Opportunity Gate passes, the listing returns to `current` and the
  opportunity is again eligible for fresh search results — assessed against
  the then-governing requirement version.
- **Member contexts (saved list, prior results, Slate-linked items)**: the
  *member* re-admits. The item keeps a `posting_changed` presentation state
  (with what-changed rendering, old vs. new version references) until that
  member opens the change review; prior review/Slate history is preserved and
  labeled historical. A member's explicit review clears the banner for that
  member only.

This makes the approved mobile "posting changed" state ("no longer shown in
current results until the latest requirements are reviewed") true in both
senses without letting one member's review change another member's view.
Pete accepts or corrects this rule at architecture acceptance.

With multiple sources, the member-facing `posting_changed` presentation is
driven by **any accepted change of the governing version** — a content
change on the governing head, or a failover that changes which version
governs — not by noise on a non-governing head. Truthful
what-changed/source-history rendering and the member's posting-changed
context apply to every such governing change, **including one whose
normalized requirement clauses are equivalent**; in that case the existing
`requirement_version` and assessments are retained (no churn). A new
`requirement_version` with re-evaluation occurs only when the clauses
materially differ (§10; one invariant with doc 02).

## 3. Criteria: draft and applied snapshot

```text
fresh visit (no restored applied state unless explicitly saved/resumed)
  ──(member request submitted)──▶ interpreting
  interpreting ──(AI returns interpretation)──▶ draft_visible
  interpreting ──(AI unavailable)──▶ draft_visible(manual)   [same surface, direct entry]
  draft_visible ──(materially ambiguous)──▶ clarifying(pre-search)
  clarifying ──(member chooses; nothing preselected)──▶ draft_visible
  clarifying ──(member dismisses)──▶ draft_visible            [unchanged draft]
  draft_visible ──(member edits: chips, Edit criteria, All filters, scope)──▶ draft_visible
  draft_visible ──(member explicit Apply)──▶ applied          [immutable applied_criteria_snapshot; search executes]
  draft_visible ──(member discards)──▶ none

applied ──(post-result refinement or clarification invoked/offered)──▶ new draft_visible
        [current applied snapshot AND current results remain unchanged]
  new draft_visible ──(member explicit Apply)──▶ new applied  [new snapshot; search reruns]
  new draft_visible ──(Keep current criteria)──▶ discarded    [applied snapshot untouched]
```

Rules (R3-4, binding):

- The interpreted draft is **visible before** explicit Apply/search. The first
  request may not silently apply an interpretation the member has not seen.
  The normal search affordance may *be* the explicit Apply action only after
  the draft is visible.
- No clarification choice is preselected; Apply stays disabled inside a
  clarification until a selection exists; a clear request receives no
  redundant clarification.
- Direct manual filters use the same draft → Apply → snapshot model
  (direct/manual parity). AI-unavailable keeps the same surface fully usable
  manually; there is no separate permanent AI mode.
- Nothing is silently searched, filtered, scoped, saved, or mutated.
  `Keep current criteria` closes/discards the new draft and never touches the
  applied snapshot.
- The doc 04 §§1–1a commands implement these transitions one-to-one, with
  two concurrency classes: **live** transitions (interpret-into-existing,
  edit, answer/dismiss clarification) rotate `draft_version_token` and
  return the full live state with the new token; **terminal** transitions
  (`apply`, `keep_current_criteria`, `discard_draft`) consume the current
  token and return an immutable terminal receipt — no new live token exists
  afterward. The exact refusal precedence is the doc 04 §1a table.

## 4. Search execution lifecycle (`search_execution.state`)

```text
submitted ─▶ retrieving ─▶ assessing ─▶ ordering ─▶ complete
   │             │             │            │
   │             ├─(non-essential check unavailable)─▶ continues; coverage=reduced
   │             ├─(index unavailable)─▶ degraded retrieval path (doc 04 §9) or failed(index_unavailable)
   │             └─(timeout/provider failure)─▶ partial or failed(reason)
   ├─(member cancels)─▶ cancelled            [no result_snapshot written]
   └─(invalid snapshot reference)─▶ failed(stale_criteria)
complete ─▶ result_snapshot written; first result selected by default
```

- Stages are member-visible as truthful progress (doc 16 binds loading copy to
  the accepted retrieval topology; no invented roles or counts before
  completion).
- `partial` writes an immutable completeness-marked snapshot containing only
  fully evaluated entries; `cancelled` writes nothing; retry is always a new
  explicit Apply (full contract: doc 04 §11).
- `reduced` coverage names *which* checks were unavailable and never upgrades
  incomplete evidence (assessments affected report `Review unavailable`).
- Interrupted search (navigation away, connection loss): execution is
  abandoned server-side by TTL; no partial snapshot becomes restorable.

## 5. Evidence grant (`evidence_grant.state`, derived from timestamps)

```text
granted ──(expires_at reached)──▶ expired
granted ──(member revokes)──▶ revoked
revoked/expired: terminal; a new grant is a new object
```

Revocation/expiry effects (doc 07 §5): every assessment whose evidence links
depend on the dead grant is recomputed without that evidence — typically
`Verified → Not established (evidence_revoked)`. Historical result snapshots
are not rewritten; they render with a "was assessed under earlier
authorization" historical label when reopened.

## 6. Assessment correction

```text
assessed(state, reason) ──(member corrects/adds evidence within grant)──▶ reassessing ─▶ assessed(new state)
assessed ──(member disputes requirement reading)──▶ flagged ─▶ reassessing ─▶ assessed
assessed ──(grant revoked/expired)──▶ reassessing ─▶ assessed(Not established, evidence_revoked)
assessed ──(new requirement_version)──▶ [no transition: a NEW assessment row is created
                                         against the new version; the old row is history]
```

Corrections are append-only history on the assessment; a prior state is never
overwritten. AI proposes reassessment output; deterministic code applies the
gate; the member sees basis and can correct again.

## 7. Saved and history (`saved_opportunity`)

```text
none ──(member saves from result/dossier)──▶ saved         [confirmation: Saved for later]
saved ──(member removes)──▶ removing(undo window) ──(undo)──▶ saved
removing ──(window elapses)──▶ removed (terminal; re-save creates a new row)
save attempt ──(write fails)──▶ none + truthful failure state, retry offered
```

Presentation overlays on a saved item (*derived*, never mutating the save):
`posting_changed`, `closed_by_source`, `could_not_reverify`, each driven by
the underlying listing state and verification timestamps. Mixed verification
states remain visible in the list (approved saved-list state).

**Saved-view search/filter contract** (carried R2 note): the Saved view's
search field and filters (`Search saved opportunities…`, `All saved ▾`,
`Verification ▾`) operate **only over the member's saved rows**, entirely
member-side, with the same draft/Apply semantics collapsed to immediate local
filtering (no AI interpretation, no snapshot, no shared-index query). Filters:
saved-state (all/current/changed/closed/unreachable), verification outcome at
last assessment, free text over role title/employer. This is a member-data
query and must be authorized like any other member read (doc 08 §3).

## 8. Slate create/continue (`slate_link`)

```text
none ──(member explicit "Review in Opportunity Slate", first use)──▶ confirming
confirming ──(member confirms; private-workspace semantics shown)──▶ creating ─▶ linked
confirming ──(member cancels)──▶ none                        [nothing created]
creating ──(Slate-side failure)──▶ none + truthful failure; retry; no orphan link
linked ──(member opens again)──▶ continue existing workspace  [no second create]
linked ──(Slate workspace deleted on Slate side)──▶ unlinked  [history label; no cascade delete of the save]
```

- Save never creates a Slate; Slate creation never saves; both never notify an
  employer or begin monitoring.
- Exactly one active link per (member, opportunity) — continue, don't
  duplicate. The handoff payload and capability dependency are doc 11 §4.

## 9. Canonical opportunity: dedupe, merge/split, governing source, aggregate eligibility

### 9.1 Linking and duplicate resolution

```text
new listing ──(exact candidate-key match, doc 05 §4)──▶ linked to existing canonical
new listing ──(near-match ≥ review threshold)──▶ link-review queue ──▶ linked | new canonical
new listing ──(no match)──▶ new canonical_opportunity
```

### 9.2 Merge/split (with full provenance)

```text
two canonical rows ──(dedupe confidence ≥ merge threshold + rule check)──▶ merged
  [survivor keeps opportunity_key; loser row becomes tombstone pointing at survivor;
   loser's linked listings re-link to the survivor; member references FOLLOW the
   tombstone transparently but keep their original key]
merged ──(correction: merge was wrong)──▶ split
  [tombstone reactivated; listings re-link back; member references re-resolve;
   both histories preserved]
```

Member-side rows never change keys during merge/split; resolution happens at
read time through the tombstone, so an incorrect merge is fully reversible
without touching member data. Every merge/split records actor, evidence
(matched keys/confidence), and timestamps in the canonical history.

### 9.3 Deterministic governing source and version

Re-run whenever any linked head or its policy changes. Among linked heads
that are **rights-permitted and in `current`**, select by, in order:

1. declared source-priority class from `source_policy` (e.g. direct
   employer/ATS above licensed feed above permitted public) — a declared
   policy fact, **never paid placement or paid relevance**;
2. completeness: deterministic count of populated governed identity/content
   fields on the head's current version;
3. freshness: `last_successfully_verified_at` descending;
4. stable final key: lowest `listing_key` lexicographically (total order).

The **governing version** is the governing head's current `source_version`;
`requirement_version` derives from it, and display fields default to it.

### 9.4 Aggregate eligibility and removal

The opportunity is eligible for current results while **at least one
rights-permitted `current` head passes the doc 05 §6 gate**. When no head is
eligible, it leaves current results and the member-facing truth follows the
most recent governing head's state (closed / could-not-reverify / stale),
with per-source truth listed in Sources & freshness. Loss of one non-governing
head never removes the opportunity by itself.

### 9.5 Failover

When the governing head leaves eligibility (closure, rights loss/expiry,
unreachable, stale) and another eligible head exists, §9.3 re-runs. The new
governing version's normalized requirement clauses are compared to the
current `requirement_version`: **materially different → a new
`requirement_version` is derived** (new assessments per §6; member evidence
and evaluation history are unchanged and re-evaluated against the new
version); equivalent → the `requirement_version` is retained. Either way the
canonical history records old head, new head, reason, and timestamps, and
members see the §2 `posting_changed` truth for the governing change —
assessment churn happens only when a new `requirement_version` was
derived.

### 9.6 Source disagreement and field-level provenance

Displayed facts carry field-level attribution to the exact source version
supplying them. By default the governing version supplies every field; a
field it lacks may be supplied by the next head in §9.3 order, attributed to
that source. When permitted sources disagree on a fact, the governing value
is displayed with attribution and the disagreement is recorded and
surfaceable ("sources differ") in Company & source / Sources & freshness —
conflicting facts are **never silently synthesized, blended, or averaged**.

## 10. Cross-machine consistency rules

- A `result_snapshot` entry binds the exact `requirement_version_key` it was
  assessed against; later listing/requirement changes never mutate it
  (stale-result truth, doc 04 §8).
- Listing lifecycle transitions emit content-free observability events
  (doc 12); member-side transitions emit content-free member-action events
  with no criteria/evidence text.
- Every machine's failure path lands on a truthful, recoverable member state —
  never a silent retry loop or an invented success.
- A governing-source change (content update or failover) creates a new
  `requirement_version` only when the normalized requirement clauses
  materially differ (§9.5). Assessments always bind to their exact
  `requirement_version`, so member evidence and evaluation history are never
  rewritten — they are re-evaluated against the new version (§6).

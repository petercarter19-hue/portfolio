# PS-INTERVIEW-AI-EXTRACT-001 — parity evidence (correction round)

## Oracle

The oracle is **40 fixtures** under `tests/interview_ai/fixtures/parity/`,
recorded by `scripts/interview_ai/record_parity_fixtures.py` against the
**untouched legacy Interview routes** at source checkpoint
`73c4e63dc74a2e67fb6bed0ed4c3d9e58e3525c5` (Interview code byte-identical
to branch base `5322f105`):

- **32 fixtures** recorded before any extraction code existed (oracle
  commit `7e3f97f7`; the first candidate's documents miscounted these as
  31 — corrected per C11).
- **8 fixtures** recorded post-rejection (correction C10) from the same
  checkpoint via a detached provenance worktree: public `best_practice`
  follow-up, public `compare` follow-up, and six authenticated variants.
  In that same recording run the 32 committed fixtures re-recorded
  byte-identically **to the committed tree** (recursive diff).
- **Stated precisely against oracle commit `7e3f97f7` (finding B6): 30 of
  the 32 original files are byte-identical to that commit.** The other two
  (`followup_member_history_success.json`,
  `followup_context_mismatch_400.json`) differ from `7e3f97f7` by exactly
  one line each: the recorded signed `context_token` value in the step-2
  *request record* was replaced with the `__STEP1_CONTEXT_TOKEN__`
  placeholder in commit `cea5ec67` — a deliberate secret-scanner
  normalization of recorder metadata, now produced natively by the
  recorder. The oracle's comparison surfaces (provider bytes, response
  bytes, statuses) in those two files are untouched, and replay chains its
  own step-1 token, so the normalization is outside every parity
  assertion. Any earlier statement that all 32 were byte-identical to the
  oracle commit was imprecise and is corrected here.

Recording used a deterministic capture fake in place of
`client.messages.create`, a fixed signing key, and a frozen clock
(itsdangerous time pinned to `1755648000`). Authenticated fixtures drive
the real authenticated seams — the Studio flag, `get_current_identity`,
and ownership resolution — with recorded synthetic identities, so the
owner (fixture-evidence) and member (empty-evidence) context construction
paths are exercised without any real identity or database. No live
provider call, no Anthropic traffic, no paid evaluation, and no production
member data were involved anywhere.

Each fixture records, per step: the request; the provider-call count and
order; each call's exact keyword set (`model`, `max_tokens`, `system`,
`messages` — nothing else, proving every optional provider parameter stays
omitted); model and `max_tokens`; the exact UTF-8 system and user-message
bytes (base64-framed); message roles and ordering; the scripted reply or
raised pinned-SDK exception; the exact response body bytes; the HTTP
status; the content type; and the database calls observed (always none —
the legacy routes never touch the database).

## Replay

`tests/interview_ai/test_parity_replay.py` replays every fixture against
the extracted runtime (bundles + release resolution + rendering + the C1
guarded job cores) under the recorded release set, asserting byte
equality on every recorded surface, plus the two operational-delta
boundaries: the expected `server_call` row count per fixture (0 for every
pre-provider refusal) and response invariance under telemetry-append
failure. Replay result: **pass, zero differences, 40 of 40**.

## Coverage

| Area | Fixtures |
|---|---|
| coach success (minimal, role context + suggestions, fenced JSON, situational family) | 4 |
| coach failure (no JSON, missing field, unauthorized evidence, provider timeout) | 4 |
| coach pre-provider refusals (415, missing answer 400, unknown profile 404, long context 400) | 4 |
| revision success (full context, no selected evidence) + refusal (unknown evidence 403) + failure (invalid reply 502, rate-limited 500) | 5 |
| planning_hints success (2 hints; 3 hints video) + failure (1 hint 502) + refusal (missing question 400) | 4 |
| grounded success / insufficient (computed) / no-citation 502 / provider 529 → 500 | 4 |
| generic success / cites-evidence 502 | 2 |
| Compare: success (grounded→generic order), grounded-failure short circuit (one call only), generic failure (two calls) | 3 |
| Signed follow-up, member_history: chain (token round-trip), opportunity-digest mismatch 400 (zero calls on refusal step) | 2 |
| Signed follow-up, best_practice chain (C10) | 1 |
| Signed follow-up, compare chain — four provider calls across two steps, prior-illustrative isolation (C10) | 1 |
| Authenticated (C10): owner review (fixture evidence), member review (empty evidence), marker gate 400 (zero calls), member grounded insufficient, follow-up refusal 400 (zero calls), nudge | 6 |

## Boundaries stated honestly

- Authenticated fixtures reproduce identity and ownership through
  recorded synthetic seams (`get_current_identity`, `is_owner`); the
  profile/evidence construction they exercise is the real production code
  path for owner and non-owner members. The identity-storage outage and
  signed-out JSON refusals remain covered by the pre-existing
  authenticated-path expectations in `tests/test_interview_studio.py`.
- The signed context token is byte-compared under the oracle's fixed key
  and clock; under production keys the token differs by construction
  (HMAC), while the signed payload and validation semantics are unchanged
  code.
- Fixture `context_token` request fields store the step-1 placeholder, not
  the recorded signed value (replay chains its own token); this keeps
  token-shaped strings out of the repository for the secret scanner's
  sake.

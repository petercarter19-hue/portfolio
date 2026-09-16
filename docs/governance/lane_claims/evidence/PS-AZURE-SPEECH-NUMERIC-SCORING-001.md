# PS-AZURE-SPEECH-NUMERIC-SCORING-001 evidence

## Accepted architecture and authority boundary

- Protected package: `PS-AZURE-SPEECH-NUMERIC-SCORING-001`.
- Authoritative implementation base: `cb61388a0e7f7bcfa09ea6964564ef38d00201ec`.
- Owner outcome reference:
  `continuity:event:evt-f429d521-3e71-4cf8-b1b2-668c037715e5`.
- Parent architecture owner: root task
  `01a09d58-4477-7b43-873a-0af993f00c85`; sole writer:
  `session:01a0a719-0e0b-73f0-9b82-4d135d71692a`.
- Exact writer telemetry observed `gpt-5.6-sol` at `xhigh`; service tier was
  unavailable. Configuration and observed model/effort agree.
- Repository authority is through merge. Production, deployment, schema,
  production data, live Azure, provider, audio generation, resource, role,
  secret, billing, schedule, marker, and enablement authority remain withheld.

## Reproduced defect and historical boundary

- Azure DevOps run 3013 used repository source
  `74e2d9fd313bf983ab6574c4b53ab52ea9e826a6`. Its aggregate-only report
  recorded the fictional `low_pitch` profile at 60.0% required-term recall and
  overall quality failure.
- The actual run-3013 transcript was intentionally discarded under the privacy
  contract. This correction cannot claim the historical provider transcript's
  exact contents or prove that scorer formatting was its actual failure cause.
- The offline counterfactual is exact and reproducible from the committed
  run-3013 fixture: the original fictional text scores 100.0% term recall;
  changing only `one point eight` to `1.8` and `September fourth` to
  `September 4th` scores 60.0% and fails under the old scorer. The pre-change
  reproduced metrics were 71 milli word error rate, 600 milli term recall, and
  `quality_passed=false`. This proves a scorer defect independent of the
  unavailable historical transcript.
- Run 3013's one-use authorization was consumed and will not be replayed. This
  package performs no fresh paid proof and does not alter historical markers.

## Scoring contract

- Add deterministic, evaluation-only English canonicalization applied to the
  expected text, observed transcript, and required terms.
- Support the bounded corpus-relevant grammar for cardinal counts, signed
  decimals, USD dollar phrases/symbols, month/day cardinal or ordinal forms,
  and the supported twenty-twenty style year. Equivalent examples include
  `five`/`5`, `seven`/`7`, `zero`/`0`, `one point eight`/`1.8`,
  `one dollar`/`$1`/`1 dollar`, `September fourth`/`September 4th`/
  `September 4`, `October fifteenth`/`October 15th`, and
  `twenty twenty-six`/`2026`.
- Preserve numerical meaning before punctuation is stripped. Wrong values,
  decimal placement, signs, month/day, currency, and units remain distinct.
  Unsupported numeric spans stay opaque rather than leaking partial credit;
  for example, `one hundred` cannot satisfy required term `one`.
- Required terms use exact contiguous token-sequence matching. Substrings and
  embedded words do not count; `one` cannot match `someone`, and `seven`
  cannot match `seventy`.
- No network, provider, model, LLM, broad fuzzy matching, or general NLP
  framework is permitted. Ordinary lexical normalization remains stable.
- An explicit scoring contract version is part of the fixture contract digest,
  and the persisted progress schema version advances. Old versions and old
  digests are refused, so aggregates produced under earlier semantics are not
  reclassified or reused. No transcript retention or broad schema migration is
  added.
- Existing WER, term-recall, token-ratio, and punctuation thresholds remain
  unchanged. In particular, 4 of 5 required terms remains 80% and can pass the
  unchanged 70% threshold. `success_marker_eligible` continues to track the
  bounded spend target independently from quality.
- All eight fixture profiles, original fixture text and required-term data,
  audio/spend ceilings, provider transport, pipeline, schedules, marker keys,
  authorization references, one-use/non-replay controls, privacy, and
  spend-versus-quality semantics remain unchanged.

## Completed offline verification

- The exact historical-format counterfactual now reaches 100.0% required-term
  recall. The eight exact reference cases and repeated samples pass.
- Numeric, date, USD currency, and supported-year equivalents pass. Wrong
  values, decimals, signs, dates, currency/units, unsupported scales, and token
  boundaries each lose the precise affected term credit while the unchanged
  70% threshold remains intact.
- Review correction probes preserve Unicode minus and consume unsupported or
  embedded numeric spans: `−1.8`, `1.8e3`, `7up`, `1abc`, and `one trillion`
  each miss exactly one term in the five-term probe (800 milli recall).
- `positive one`, `plus one`, `+1`, and `one` normalize equivalently. The
  actual-form `September fourth, twenty twenty-six`, the same phrase without
  its comma, and `September 4 2026` normalize equivalently; wrong day and year
  remain distinct.
- Progress schema v2 and pre-versioned contract digests are refused. The
  scoring contract version is bound into the current fixture digest.
- Writer verification on candidate
  `f66400cf8297b00d5b7ff932f378723322f2258a`: 34 focused Speech tests pass;
  the required 308-test Speech, marker-runner, package-registry, and delivery
  preflight set passes; `git diff --check` and Python AST parsing pass. The
  default dry run planned all eight cases with zero provider requests, zero
  completed requests, zero generated audio, and $0 estimated spend.
- Self-review found no remaining contract violation. No provider, Azure,
  marker, audio, paid, deployment, role, resource, secret, or portal operation
  was performed.

## Independent review

- The initial candidate `1496494a43c26ac9195947aa1aec4d439813ca45`
  received `REVISE`: unsupported or embedded numeric spans leaked partial term
  credit, Unicode minus was erased, positive signs were inconsistent, and the
  supported no-comma word date/year form was not segmented correctly.
- The sole writer corrected only those findings and froze
  `f66400cf8297b00d5b7ff932f378723322f2258a`.
- Independent reviewer `agent:/root/speech_scoring_review` accepted that exact
  candidate with `PASS`. The reviewer independently ran all 34 Speech tests,
  checked the complete diff and exact clean remote candidate, confirmed the
  five wrong-value probes at 800 milli recall, confirmed positive-sign and
  comma/no-comma date equivalence, and confirmed wrong-day/year distinction.
  The reviewer was configured for `gpt-5.6-sol` at `high`; native runtime
  telemetry and native reviewer identity were unavailable and are not claimed.

## Delivery state

- Activation PR 1054 passed required Azure build 3046 and merged at
  `cb61388a0e7f7bcfa09ea6964564ef38d00201ec`.
- Implementation and independent exact-candidate review are complete at
  `f66400cf8297b00d5b7ff932f378723322f2258a`. The fixed receipt records the
  accepted review. Implementation PR/CI, accepted merge, and claim close are
  pending.
- No claim is made that run 3013 passed, that paid charges were recognized, or
  that scheduled Speech enablement is complete.

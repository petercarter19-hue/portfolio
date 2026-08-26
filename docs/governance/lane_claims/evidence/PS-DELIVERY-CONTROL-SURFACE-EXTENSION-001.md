# PS-DELIVERY-CONTROL-SURFACE-EXTENSION-001 — delivery evidence

Runtime-inert record. Protected Delivery Control child; independent exact-SHA
review required and obtained.

## Outcome

An active package's exact assigned writer can append a newly discovered,
already tracked file to that package's `surfaces` without pausing, transferring,
or reopening the work. The `extend-surfaces` transition runs only from a fresh
dedicated control branch in the leased `_control` singleton, changes only the
target claim JSON, and leaves production and deployment authority withheld.

The old surface list must remain an exact prefix of the new list. Each addition
must be a normalized repository-relative path proved as a Git blob on current
`origin/main`. The transition reruns the full current claim set and refuses
same-claim, exact, parent, child, case-variant, cross-package, and control-path
overlap. It also refuses stale main, dirty state, a wrong branch, package, task,
or lease, inactive claims, malformed or duplicate values, broad or unproved
paths, unrelated files, and any non-surface claim-field change.

## Exact invocation

Use the active target claim's existing `writer_ref` for `<WRITER-REF>`:

```bash
python scripts/worktree_lifecycle.py control --package <PACKAGE-ID> --task-ref <WRITER-REF> --branch work/YYYY-MM-DD-delivery-extend-surfaces-<slug> --base origin/main --execute
```

Append only the required tracked file path at the end of that claim's
`surfaces`, commit only that claim JSON, then run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent extend-surfaces --task-ref <WRITER-REF> --fetch --require-clean
```

After the control PR is accepted, release the clean lease:

```bash
python scripts/worktree_lifecycle.py finalize-task --task-ref <WRITER-REF> --execute
```

## Review and correction

- `1a988c7f0fcf39ff6c4094bb1d024d2b48b3152f`: independent REJECT for four
  fail-open gaps involving null-key field deltas, same-claim overlap,
  heuristic missing-path acceptance, and advisory lease proof.
- `435713fbbd2bacce7d9e89dce217dfdf6ebe1318`: corrections independently passed.
  PR build 1644 then exposed one unrelated presentation defect: the duplicated
  workflow paragraph exceeded the existing lean-document gate.
- **`59ea3a79ee1bde367bb33baec3c30fcbd7b3850c`: independent PASS.** The
  implementation and tests are unchanged from the prior passing SHA; duplicate
  workflow guidance is removed, while `START_HERE.md` retains the exact command
  and leased-control sequence. No Workshop path is present.

The reviews were static and read-only. The writer executed the tests below.

## Verification

- `python -B -m unittest tests.test_delivery_preflight tests.test_worktree_lifecycle -q`
  — **122 passed** on the final implementation/test bytes.
- PR build 1644 executed **4,084 tests**; its only failure was the now-corrected
  AI workflow word cap. The final file is restored from 1,226 to **1,098 words**.
- Positive fixture: append `tests/test_database_service.py` after
  `services/database_service.py` in an active target claim — pass.
- Negative fixtures cover every delegated refusal, including missing control
  proof, non-string values, null-key field changes, same-claim overlap, and
  prospective exact/parent/child collisions.
- Clean implementation write preflight passed at the reviewed SHA.

## Boundaries and honest limitations

- This control admits only a claim-only repository PR. It does not authorize or
  perform deployment, production, schema, configuration, provider, identity,
  data, or destructive operations.
- No Workshop code, claim, candidate, database file, or test was edited or
  reviewed by this package.
- The actual Workshop surface append remains separate work for Workshop's
  assigned writer after this package reaches main.

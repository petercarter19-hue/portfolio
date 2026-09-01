# CR10 owner technical completion report

**Package:** `PS-SETTINGS-ACCOUNT-EXPORT-AVAILABILITY-001`
**Outcome:** Per-client rate limits on the three account-export routes and
a pre-download size refusal in the storage adapter, closing the second
recorded C3 gap.

## Changed paths

`owner_routes.py` (the budget mapping, declared next to the routes it
governs), `app.py` (one import, one post-registration application loop),
`services/account_export_storage_service.py` (`read_final` pre-read
guards), `tests/test_account_export_limits.py` (new file),
`tests/test_account_export_storage.py` (one new test class for the
pre-read guards), the C3 contract document (gap bullet retired), and this
package's docs and governance records.

## Tests

New limits file (eleven tests) plus four pre-read tests in the storage
file; full suite run green locally before push. All offline; no
database, storage, or network. The 429 test breaches a real budget
through the app's own limiter and asserts the static content-free answer
is identical across different job keys, and a HEAD-burn test proves the
verb Flask serves implicitly alongside GET consumes the same budget
(the independent review's HIGH finding against the first candidate).

## Merge, deployment, schema state

Repository merge only. Nothing deployed; no flag changed; production
authority withheld throughout. The export feature remains OFF and the
worker still runs nowhere. Note the limits protect the routes even while
the flag is off: the limiter runs before the view, so the flag-off 404
path is budgeted too.

## Honest limitations

- The download budget shipped as 30/hour rather than the first-scouted
  6/hour, and the independent review ruled 30/hour stands: 6/hour proved
  empirically below the closed experience package's own one-process test
  choreography (11 download-route requests). That file was editable in
  principle through the governed extend-surfaces transition; it was not
  edited because re-choreographing a closed package's recorded green
  suite would mutate what its review receipt attests. Ruling and burst
  disclosure (30 may arrive at once: up to ~2.93 GiB of concurrent
  buffering per address) recorded in CR10_EXPORT_AVAILABILITY.md.
- Budgets key on the forwarded client address for this surface, not the
  member; accepted for v1 and recorded in CR10 with the member-keying
  refinement as future work.
- The limiter counts in process memory per instance; the existing app.py
  note about Redis-backed storage for multi-instance production applies.
- A browser that trips a budget on these HTML routes receives the
  app-wide static JSON 429 sentence, not an HTML page; accepted as
  cosmetic.
- The remaining C3 bullet — expiry is not deletion — stays open and
  belongs to the worker/operations slice, not this package.

## Next action

Independent review, merge, close.

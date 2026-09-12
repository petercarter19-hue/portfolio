# PS-MVP1-MEDIA-BACKEND-001 candidate evidence

Runtime-inert post-review record. The required independent exact-SHA review
passed. This file does not change application behavior.

Activation PR 1001 squash-merged as
`cfbb884b5581d3e745dc0bbf7fae6e11c0e477df`. The active Protected claim assigns
implementation to sole writer
`session:01a0935a-1de0-7d33-8214-14a28e24e80b`; production authority is
withheld.

Exact reviewed candidate
`9baca22208ddb3ca72a225252159539f25c64af7` changes only the claimed isolated
backend media service, repository, and focused tests:

- `services/resume_media_service.py`
- `services/resume_media_repository.py`
- `tests/test_resume_media_service.py`
- `tests/test_resume_media_repository.py`

Package C surfaces, routes, shared app/API registration, UI, SQL and schema,
production configuration, live identity and providers, public delivery, and
deployment are unchanged.

## Outcome

The bounded backend contract provides owner-scoped private-photo readiness,
a separate synthetic generated-illustration catalog, versioned selection and
finite slot crops, private preview and Add, words-only behavior, and later
immutable publication for `story_banner` and `experience_support`.

The contract fails closed on stale, deleted, restricted, withdrawn, mismatched,
or changed media; authorizes before bytes and rechecks after reads; derives
commit validation from the exact placements being persisted; provides
convergent idempotent replay; uses generation-fenced keyset pagination; and
keeps provenance and rights metadata immutable and safely allowlisted. Artwork
is never projected as member biography or evidence.

## DeepSeek implementation record

The sole DeepSeek implementation session was
`01a09374-a444-72f2-928d-09c3dcd4b197`. It completed one implementation turn
and two reviewer-directed correction turns in 29 minutes 35.383 seconds of
worker time. The final cumulative session snapshot reports 67,871,837 input
tokens, including 67,099,520 cached and 772,317 uncached input tokens, plus
262,288 output tokens (125,426 reasoning). Cached input is part of input and
cumulative snapshots were not summed.

An earlier launch was interrupted when the owner closed the app before it made
workspace changes. Its usage is unavailable and it is not classified as a
DeepSeek failure. The controller was configured for the personal DeepSeek
provider, `deepseek-flash`, high effort, lean context, and workspace-write. The
controller verified the exact session UUID on every continuation; its own CLI
event does not attest provider or model, so configured and verified fields are
kept distinct.

## Verification and independent review

The manager reran 109 focused tests and 6 available compatibility tests with
`python -B`; all passed. Independent read-only reviewer
`agent:/root/d_media_review` reviewed exact candidate
`9baca22208ddb3ca72a225252159539f25c64af7`, reran the 109 focused tests, and
passed three additional adversarial probes covering placement substitution and
rollback, provider source substitution, and complete private-safe review
projection. It returned PASS with no medium-or-higher findings.

Two earlier reviewer passes returned REVISE and drove the two bounded correction
turns. The final PASS belongs to the independent reviewer, not the implementer.
This receipt and evidence file are the only post-review repository tail.

## Release truth

The evidence remains synthetic and in-memory. It does not prove a real SQL or
cross-store transaction, multi-process behavior, Blob storage, Defender scan,
live Photo Capture, live identity, production catalog or rights qualification,
public media delivery, schema application, or deployment. A merge is not a
deployment, and production authority remains separately withheld.

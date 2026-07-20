# PS-CAPTURE-PHOTO-LIFECYCLE-001 - Proof-Mode Admission Audit Record

## The gap this closes

`CAPTURE_PHOTO_LIFECYCLE_PROOF_RUN_ID` was parsed, regex-validated, and stored
on `PhotoLifecycleConfiguration` by the released gate - and then consumed
nowhere in application code. It appeared only in its own unit tests.

Every other logger call on the Photo paths is an error branch: storage
unavailable, identity unavailable. Nothing was written on a success path.

The consequence for an attended production proof window was serious and easy to
miss. The window would have produced **no positive server-side record** that
proof mode was ever active, or that a cohort member was ever admitted. The
entire evidence chain for the most sensitive control in the package - a
production feature-flag bypass - would have rested on operator screenshots,
which prove what a browser displayed, not what the server decided.

## What is emitted

One line, at warning level, from
`services/photo_lifecycle_access_service.py`:

```text
PeerSlate Photo lifecycle proof admission. access_mode=proof run_id=<run id>
```

When the optional run id is not configured, the label is `unset`.

The format string is the module constant `PROOF_ADMISSION_LOG_FORMAT`, so the
evidence and the tests that police it cannot drift apart.

## What it carries, and what it can never carry

It carries exactly two values:

| Field | Value | Why it is safe |
| --- | --- | --- |
| `access_mode` | Always the literal `proof` | A mode name, not a secret. It is the fact being proved. |
| `run_id` | The nonsecret bounded correlation label | Already specified as nonsecret in the configuration contract: package ID plus a date or run number, no identity and no record key. Constrained by the server to `^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$`. |

It never carries, and no code path allows it to carry:

- the admitted `user_key`, or any user key;
- either cohort key, or the cohort size;
- the configured expiry;
- the source key, Capture key, Blob name, container, account, or SAS;
- any email, external subject, issuer, token, or header;
- any member content, note, filename, or image data; or
- the `PhotoLifecycleConfiguration` object itself.

The service docstring rule that the configuration object must never be
serialized into a log record is preserved. The single narrow exception - two
named safe fields - is enumerated in the dataclass docstring itself so it
cannot widen by accident during a later edit.

## Granularity, and why

**One record per proof window, per application worker process, emitted on the
first request that proof mode actually admits.**

The dedupe fingerprint is `(mode, run_id, expires_at_utc)`, held in process
memory. It deliberately **excludes the cohort keys**, so the audit path retains
no identity material at all.

Rejected alternative - one record per admitted request:

- The Photo UI polls the status endpoint while a scan is pending. Over a
  two-hour window with two synthetic owners running a full lifecycle, that is
  hundreds of identical lines. The one fact worth proving would be buried in
  its own noise.
- Per-request volume and timing correlate with cohort member activity, which is
  a side channel about the synthetic identities that serves no evidentiary
  purpose.

Rejected alternative - one record per admitted identity:

- The lines would be textually identical, so a reader could not distinguish two
  members from one member twice. It adds volume without adding evidence.

What the chosen granularity still proves:

- Proof mode was **live in production**, not merely configured.
- The server **actually admitted** a cohort request - configuration alone does
  not emit the line.
- It happened under **this exact run id**, which ties the log to the run record.
- A **second window can never be silently attributed to the first**: a new run
  id or a new expiry is a new fingerprint and produces a new line. An operator
  who re-opens the window after the two-hour expiry lapses gets a second line,
  correctly.
- Multiple worker processes each emit once, which is corroboration rather than
  noise.

## Why warning level

This application configures no logging handlers or levels of its own. Under the
default configuration an info-level record is dropped before it reaches any
handler - which would have reproduced exactly the silent evidence gap this
change closes.

Warning is also semantically correct. Proof mode is a deliberate, temporary
bypass of the ordinary release flag in live production. A record of that being
active deserves to be visible, and it follows the existing repository precedent
of `_log_interview_failure`, which records a privacy-safe warning without ever
logging content.

## Operational use

During the window, immediately after the operator sets the four settings and
Synthetic A loads `/app/capture`:

1. Confirm the line is present with the expected run id.
2. Quote it verbatim into the run log. It is committable evidence.
3. Confirm by reading it that it contains no user key, cohort value, expiry, or
   email.

**If the line is absent, proof mode is not admitting.** Stop and diagnose the
configuration before creating any production record. Absence is a real signal,
not a logging quirk.

After the gate is disabled at teardown, confirm no further admission line is
emitted. That is part of the final both-flags-false verification.

## Behaviour by mode

| Mode | Condition | Record emitted |
| --- | --- | --- |
| `proof` | Cohort member admitted | **Yes** - once per window per process |
| `proof` | Non-cohort identity denied | No |
| `proof` | Signed out or identity unresolved | No |
| `ordinary` | Ordinary release flag true | No - this record is specific to proof mode |
| `off` | Both flags false | No |
| `invalid` | Both flags true, malformed cohort, missing/expired/oversized expiry, malformed run id | No |

## Test coverage

`tests/test_photo_lifecycle_access.py`, twelve added tests:

- the record appears exactly once on proof admission, at warning level, with
  the exact expected message;
- the message and its log arguments contain no user key, no cohort value, no
  email, and no expiry - asserted per forbidden fragment, and asserted
  positively that the argument set is exactly `{proof, run id}`;
- no record in `off` mode;
- no record in `invalid` mode, across four distinct invalid configurations;
- no record in `ordinary` release mode;
- no record when a non-cohort identity is denied;
- one window admitting many requests still records once;
- a second window with a different run id and expiry records again, and is
  attributed to the second run id;
- an unconfigured run id is recorded as `unset`;
- the audit state can be reset for a fresh announcement;
- an end-to-end request through a real direct Photo route records the line and
  the line contains no user key; and
- an end-to-end non-cohort request through the same route records nothing and
  still returns the neutral `Photo Capture is unavailable.` 404.

## Scope

This change touched `services/photo_lifecycle_access_service.py` and
`tests/test_photo_lifecycle_access.py` only. It made no access decision change:
exactly the same identities are admitted and denied as before. No route,
schema, migration, template, CSS, or JavaScript changed, and neither Photo flag
was enabled.

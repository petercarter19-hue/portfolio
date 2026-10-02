# PeerSlate private test site

Your test site lives at `X:\PeerSlate\local-reviewer`. Double-click `Start.cmd`
on the Windows PC. On your Mac or iPad, connect Tailscale with the same account
and open the private HTTPS address recorded in `DEVICE_ACCESS.md`. Bookmark it.
Keep the PC awake while using the site. Closing the browser preserves saved work.
`Stop.cmd` stops only this site. No Windows Sandbox or review ZIP is part of
ordinary use.

Stop acknowledges promptly, refuses new work and finishes the current request
before closing. Status reports when it is stopping. Updates wait for that work
and process shutdown to finish before promoting another version.

Private mode has one local **Private Test Profile**. It may hold your work-history
documents after private setup and acceptance. The placeholder name does not
anonymize those files. They remain on this PC; using AI sends the selected content
to the configured Azure AI service. Test publication stays within the private
site and does not publish to peerslate.com. AI proposes changes for your review.

Real Azure providers serve extraction, career interview, synthesis, visitor
questions and Speech. The allocation allows **up to 100 operations per feature
for the entire installation**, including acceptance checks, within fixed spending
limits. Each call reserves its full maximum before connecting; successfully
validated completion records its measured usage. Restarting, restoring content
or changing a display name does not replenish the allowance. Timeouts or uncertain
usage retain the reservation and block further calls for that feature until the
accounting can be investigated. There is no automatic retry or reset.

The accounting uses conservative operator rates, not an Azure invoice or a
provider billing guarantee. Speech uses an explicit assumed rate of $1.20 per
audio hour, rounded up by seconds and bounded by decoded duration; the numeric
Azure tariff has not been verified. Empty authorized public previews use no AI
money, but still consume an operation. Source/citation reads do not consume AI
allowance. A failed or exhausted provider reports unavailable rather than
substituting a simulated answer.

The site runs the actual Resume/MVP1 Profile routes using local persistent stores.
It is a focused test environment: unrelated navigation and production SQL/Blob
services remain unavailable. This is local acceptance, not proof of production
identity, SQL, storage or deployment. Source acceptance is recorded separately
from the installed candidate label.

## Privacy and device access

The app listens on `127.0.0.1:53720`. Tailscale Serve provides the private HTTPS
endpoint on a separate port, preserving the Coding Dashboard's HTTPS443 mapping.
No public Funnel is used. The boundary verifies the exact configured HTTPS
origin and Tailscale account on every browser request, including Windows.
Demo selector cookies cannot choose the private owner. Another Tailscale account
and unauthenticated loopback browsing are refused. This PC's processes running
as the Windows user or administrator remain trusted.

Private setup restricts configuration, saved data, checkpoints and logs to this
Windows user, SYSTEM and Administrators. Startup verifies those permissions.
Files are not a separately encrypted backup service. Keep the installation on a
private Windows account and retain the matching release and controller.

Checkpoint, restore and stop require the local process token and PC loopback.
The private personal profile cannot be reset through the fictional-member reset
command. Every private response uses no-store; browser cookies are Secure and
mutations require the exact HTTPS Origin. Browser resources stay on this origin.

## Recovery

`Checkpoint.cmd` saves a recoverable copy under `checkpoints`. The authoritative
content file is `data\state.json`. Successful changed requests are saved before
the response returns. Corrupt or incompatible state stops startup without reset.

Use the private Python runtime and installed launcher for commands:

```powershell
$testPython = 'X:\PeerSlate\local-reviewer\runtime\Scripts\python.exe'
$testTool = 'X:\PeerSlate\local-reviewer\reviewer.py'
& $testPython -I -B $testTool status
& $testPython -I -B $testTool checkpoint
& $testPython -I -B $testTool restore '<exact checkpoint filename.json>'
```

Restore replaces content with the selected checkpoint and preserves displaced
content first. It never replaces `data\provider-budget-v1.sqlite3`. That ledger
is independent, persistent and cannot be automatically recreated. Preserve it
along with `private-access.json`, `live-ai.json`, `ai-allocation.json` and
`ai-factory.json`. Do not delete or rotate these files to recover an AI allowance.
The ledger cannot detect deliberate replacement by an older complete copy made
by this Windows user or an administrator; there is no external rollback anchor.

A failed public operation has a narrowly scoped local operator recovery:
`resolve-failed-public --proof <exact evidence JSON> --review <independent review JSON>`.
It requires the stopped site's exclusive lifetime lock, unchanged installation,
owner and allocation, and reviewed evidence that the original synchronous
transport and all local workers finished. Missing or uncertain evidence keeps
the fence. The command atomically records an immutable failed-operation event
and charges the entire original reservation. It preserves the consumed operation
count, caps and successful settlements; it does not invent a successful native
response, refund usage or replay the failed request. Repeating the exact event is
idempotent; conflicting, partial-settled and overrun cases are refused. Its
guarded schema2-to3 upgrade changes only accounting structure and adds the event.
Older controllers refuse schema3 rather than ignoring failure history.

## Maintainer setup and updates

Routine use requires only Start and the bookmark. Maintainers handle source
archives internally: a release requires its source commit and SHA256, reviewed
requirements overlay and SHA256, immutable controller and unchanged Python3.12
runtime. `update` validates source/runtime/content compatibility before stopping
or changing the installed pointer. No automatic Git pull or dependency update
runs. Previous releases and checkpoints are retained. A private installation
cannot roll back into the former shared fictional-account controller.

An accepted successor app whose reviewed factory pins changed uses the explicit
`update ... --candidate-state accepted-main --factory <fixed V12 interface>`.
This requires a stopped, drained private site and no active provider reservations;
resolve a failed reservation under its original app/configuration before updating.
Only the reviewed V11/V12 interfaces are accepted. Owner, signing key, allocation,
models, prices, scopes, caps and consumed counts are preserved.

The update prepares a protected, immutable pair under
`data\provider-configurations`. Its complete file hash is stored in
`installation.json` alongside the app release, so a single atomic manifest write
selects both. The root `live-ai.json` and `ai-factory.json` remain the original
configuration lineage; when a pair is selected, it supplies the active settings
and factory. Ordinary updates retain that selection. Previous manifests select
the prior pair on rollback; preparation failure leaves the old pair active.
Rollback across app or factory bindings also requires every outstanding provider
reservation to be resolved under the current binding before any content or
manifest change. The stopped worker lifetime lock remains held through that check
and promotion, so recovery cannot be stranded on another binding.
Preserve these private pair files with the data and ledger. Missing, altered or
incompatible pairs refuse startup; no fallback, allowance reset or provider call
occurs during preparation.

`setup-private --origin <exact HTTPS address> --login <exact Tailscale login>
--allocation <bound allocation JSON> --factory <bound factory JSON>` performs
one-time setup while the site is stopped. It generates one persistent owner UUID
and signing key, verifies reviewed allocation/factory bytes and source files,
sets private storage permissions and creates the dedicated ledger once. Partial
setup is retained for diagnosis; rerunning cannot mint a fresh allowance. No
provider credential or paid call is acquired during setup.

Azure AI credentials come from the existing local Azure CLI sign-in, only after
a durable reservation. Tokens, document text, prompts and answers are not written
to ordinary provider diagnostics; numerical usage and status are recorded. Dotenv and
production SQL discovery remain disabled. The old offline mode is available only
before private setup; a missing private configuration never silently downgrades.

For an independently reviewed fictional qualification, a stopped-site operator
can explicitly run `arm-public-diagnostic --fictional-qualification-only`.
This consumes a one-use permit on the next public operation and records its
bounded request/response phases under the verified private `logs` directory.
It never records credentials or headers and captures no later requests. Each
explicit permit uses a new operation-numbered directory; the same operation
cannot be rearmed or overwritten. Earlier captures remain immutable evidence.
This exception captures content: use fictional
material only and retain the evidence privately. It is not part of routine use.

## Validation

Run `python -B -m unittest discover -s tests -p 'test_local_reviewer*.py' -v` with
the reviewed dependencies. External preparation may set
`PEERSLATE_LOCAL_REVIEWER_SOURCE` to the supplied immutable source. Tests cover
persistent content and budgets, private owner binding, local control isolation,
actual provider composition with fake transports, non-content logging and
configuration failures. Independent review and bounded real-provider/device
acceptance are required before calling installation complete. A PC HTTPS check
does not establish physical Mac/iPad microphone or browser acceptance.

# PeerSlate private test site

Your test site lives at `X:\PeerSlate\local-reviewer`. Double-click `Start.cmd`
on the Windows PC. On your Mac or iPad, connect Tailscale with the same account
and open the private HTTPS address recorded in `DEVICE_ACCESS.md`. Bookmark it.
Keep the PC awake while using the site. Closing the browser preserves saved work.
`Stop.cmd` stops only this site. No Windows Sandbox or review ZIP is part of
ordinary use.

For a fresh fictional demo, double-click `Fresh Demo.cmd` while the onboarding
workspace at port8444 is selected. It saves a recovery checkpoint, clears the
fictional resume, proposals, profile and onboarding progress, restarts the site,
and opens the empty resume page. Personal data and AI allowances are preserved.
Personal selection refuses reset before stopping the site. The PC must remain
awake while the demo runs.

The command waits for current work to finish and refuses unresolved provider
reservations. If an error says **Fictional reset committed**, the data was already
cleared and its checkpoint was saved. Use `Status.cmd` to check startup, then
`Start.cmd` if stopped; do not repeat reset to fix startup. To recover the old
fictional content, stop and confirm shutdown, use `Run.cmd restore <checkpoint>`
with the reported checkpoint name while onboarding remains selected, then start.

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
`update ... --candidate-state accepted-main --factory <fixed reviewed interface>`.
This requires a stopped, drained private site and no active provider reservations;
resolve a failed reservation under its original app/configuration before updating.
Loading retains the reviewed V11/V12 interfaces and the fixed onboarding interface
`d5d09972f68ad646c0c059161fcedf131b2d77cfe4c5c022d294e71c28de95e6`.
Explicit promotion accepts V12 or that onboarding interface; V11 remains loadable
for the original installation and rollback. One validated byte snapshot supplies
both the parsed interface and its immutable pair. Owner, signing key, allocation,
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

The onboarding interface matches accepted application
`693865dda23e7b2cd5613b1e9adb783f718ce7a0`, archive SHA256
`7c6d971ab37ebc8da2189020d357dc6b19aa97501a43bc3fce106d8e282a0629`.
Only three of the twenty factory file pins differ from V12; provider contracts
and budget settings do not change. Retain the complete reviewed dependency
overlay `b6afc252bfd9ec203602bcabafbdb6064fb86cf21726b3c2c4118fd79f2a40c9`;
the waitress-only local requirements file is not its replacement. Install this
pair only from accepted, independently reviewed controller source after current
CI, using explicit stopped/drained promotion. Preserve the prior fa6/V12 pair,
both saved workspaces and their checkpoints. A prepared archive or passing source
test does not prove private installation or ordinary-browser acceptance; record
the installed app/controller identities and actual selected-origin observation,
then return personal8443 to running/ready.

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
# Fictional onboarding workspace

The private reviewer supports one separate fictional saved-state workspace on
`https://<your existing Tailscale host>:8444`. It uses your existing authenticated
development account and owner UUID. This is private testing, not product signup.
Personal content remains in `data/state.json`; fictional content stays in
`data/fictional-workspaces/onboarding/state.json`, with its own checkpoints.
The page displays **FICTIONAL ONBOARDING WORKSPACE** while it is selected.

Only one workspace runs at a time. The inactive origin is refused, including old
tabs and their writes. Keep the existing private8443 and dashboard443 Serve
mappings. Add only the private8444 mapping to the same loopback backend; do not
reset Serve or enable Funnel.

Use the installed `reviewer.py` commands with the installation's Python runtime:

1. `stop`, then confirm stopped and fully drained with `status`.
2. `create-fictional-workspace` once. It creates fresh fixture content and leaves
   personal selected. It never copies personal content or recreates an existing
   fictional workspace.
3. `select-workspace onboarding`, then `start` and `open` in your normal browser.
4. Make fictional edits, save, reload, and restart to check persistence.
5. `stop`, confirm drained, then `select-workspace personal`, `start`, and `open`.

Creation, selection and private `restore <checkpoint>` require the stopped server
lifetime lock and zero active reservations across all five provider profiles.
Private restore now runs as an explicit stopped operator command. It validates
the selected namespace before replacing content; foreign and legacy personal
checkpoints cannot restore into the fictional workspace. A failed request blocks
these actions until its supported recovery under the original context completes.

Both contexts retain the same root provider ledger, allocation, operation counts,
spending caps, signing key, and immutable application/factory binding. Switching
does not replenish AI or diagnostics. Initial fictional acceptance uses zero
provider calls. Never reset the ledger to unblock a test.

Workspace metadata is server owned. Missing or changed selection, descriptor,
owner binding, links, or saved state stops startup rather than loading personal
content. An interrupted selection retains the last complete pointer and snapshots.
Incomplete creation is preserved and refused rather than silently reset. Updates
probe and retain the selected context. Rollback requires a compatible controller
and the exact same selection; it validates current content and does not rewind it.
Use explicit restore for a deliberate content rewind. Older controllers are refused
once the workspace contract exists, including after return to personal.

Mac/iPad hardware, microphone use, and actual product signup remain separate
acceptance items. This capability does not enable or publish the public MVP.

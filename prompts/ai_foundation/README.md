# AI foundation prompt contracts

Prompt text is versioned by product adapter. The shared foundation does not
define one universal persona or one giant system prompt.

Every product prompt must:

- use only supplied, request-authorized source versions;
- emit claim-level citations with exact source-version keys and spans;
- label interpretation separately from evidence;
- state meaningful limitations and unknowns plainly;
- never imply private information was searched from a public request;
- never save, publish, send, delete, or make canonical changes; and
- produce no factual claims in refusal or unavailable states.

Ask Pete's first reference contract is
`ask_pete_recruiter_brief_v1.md`. It exercises the shared contract without
wiring a route, selecting a provider, or establishing runtime configuration.

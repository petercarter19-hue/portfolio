# PS-INTERVIEW-PUBLIC-GATE-001 — Route, Data, and Truth Boundary

## Public demonstration contract

The current Studio is a public product demonstration rendered from Pete's already-approved public profile data. A visitor may type or dictate their own practice answer, request coaching, ask for a generic best-practice example, or request an example grounded in Pete's public history. These are different identities and must not be blurred.

Use plain labels near the relevant choice:

- **Your practice answer:** belongs to the visitor's current practice flow.
- **Best-practice example:** generic and illustrative; it is not the visitor's or Pete's real experience.
- **Use Pete's public history:** grounded only in the approved public profile data supplied to this page.
- **Compare:** presents both labeled outputs without merging their truth status.

Do not use “Use my history” on this public Pete demonstration when “my” could be interpreted as the visitor.

## State and transmission matrix

| State or action | Where it exists | Honest public label |
|---|---|---|
| Typed draft | current browser storage | saved in this browser; not account-synced |
| Completed attempt/history/goal | current browser storage | this browser's practice data; clearable from this browser |
| Submitted question and answer for coaching | PeerSlate request/response path | sent to PeerSlate for coaching when submitted |
| Approved public-history grounding | current public page/server request | uses the named public profile's approved history only |
| Camera rehearsal | local browser media APIs | recording is not uploaded, analyzed, or retained by PeerSlate |
| Browser speech recognition/transcript | implemented browser capability | describe the real browser/transcript path and fallback; do not imply stored voice Capture |
| Authenticated private history | not implemented on this route | future owner workspace; never label browser data as this |

## Route contract

- Public demonstration: `/interview-studio`
- Browser-local public history view: `/interview-studio/history`
- Future owner workspace reservation: `/app/interview-studio`

The future owner route will require trusted-session identity, owner-scoped persistence, retention/deletion/export controls, and permitted private-history retrieval. None of that may be approximated in this front-end package. The public route stays useful without pretending to be signed-in product behavior.

## Data restrictions

- Use only the server-provided public profile/evidence payload already rendered by the current route.
- Do not add static copies of résumé/history data to JavaScript or HTML.
- Do not inspect or expose Capture/Moment/private owner records.
- Do not persist model answers, visitor answers, or camera media anywhere except the existing explicitly disclosed browser-local behavior.
- Do not create or update canonical records from public practice.

## Failure honesty

When local storage, speech recognition, camera permission, JavaScript, or an AI request is unavailable, keep the page usable and state what failed. Never replace an unavailable capability with a success-looking simulation.

# PeerSlate Manager/Writer Handoff

Use this only when another task will continue an active branch, take shared
surfaces, or resolve a real cross-claim decision. A self-managed implementation
writer continuing through PR and merge needs no handoff.

## Required transfer record

- Package and one-sentence outcome
- Routine, Bounded, or Protected
- Opaque from/to task references and explicit relinquishment
- Branch, authoritative base SHA, and exact pushed checkpoint SHA
- Claimed and forbidden paths/domains
- Completed work and verification
- Open finding or owner decision
- Repository state and production state, separately
- One next action

Do not require or record a person's legal name, account identity, email,
credential, MFA, token, cookie, or session material. Chat history alone is not
an ownership transfer.

For an in-place transfer, the prior writer first commits, pushes, and stops.
From current main, create a dedicated
`work/YYYY-MM-DD-delivery-transfer-<slug>` control branch. Change only the
claim's `writer_ref` and `handoff` object. The handoff must contain opaque
`from_ref` and `to_ref` values, the exact pushed `checkpoint_sha`, and
`relinquished: true`. Commit, then run:

```bash
python scripts/delivery_preflight.py --package <PACKAGE-ID> --intent transfer --fetch --require-clean
```

Merge the one-claim control PR before the receiver writes. Stop if the pushed
SHA, relinquishment, or collision proof is missing.

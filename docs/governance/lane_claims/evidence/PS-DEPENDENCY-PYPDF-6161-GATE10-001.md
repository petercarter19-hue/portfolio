# PS-DEPENDENCY-PYPDF-6161-GATE10-001 evidence

This is the runtime-inert closeout tail for the minimum dependency correction
needed to restore Azure PR validation for Settings Account Export Gate 10.

- Owner authorization: `pete-chat-2026-09-02/settings-account-export-gate-10-enable-and-proof`, followed by Pete's direction to complete every required unblocker in this task.
- Base: `f59dfc5e1065228d6180604b10ed184384ae4545`.
- Reviewed candidate: `629204ee1faed7f377653af324bfa7215c0cfbeb`.
- Runtime change: `requirements.txt` pins `pypdf==6.16.1` instead of `6.15.0`; no other dependency or product file changed.
- Dependency proof: fresh isolated Python 3.12 resolution succeeded and `pip-audit==2.9.0 --strict` returned `No known vulnerabilities found`.
- Consumer proof: the untouched remote `work/2026-09-01-myopp-member-import-001` source was read through a temporary archive, never written or checked out; its `tests/test_my_opportunities_member_import.py` suite passed with 154 tests, 2 subtests, and 2 skips against pypdf 6.16.1.
- Review: complete-diff self-review passed under the Bounded path. The candidate contains the one-file claim activation and one-line dependency pin. The activation PR carries the pin and review tail as the recorded owner-directed minimum exception because the vulnerable target dependency prevents a claim-only PR from passing the required Azure policy.
- Production: withheld. This package does not deploy, enable, change schema, mutate configuration, or touch identities.
- Scope preservation: My Opportunities code, claim, branch, and durable worktree were not modified; the older unmerged dependency activation branch remains untouched and non-authoritative.

# GPT-6.1 Sol assignment defaults

Routine documentation correction selected by Pete on September 29, 2026.
The site manager is the sole writer. This does not change product AI models,
provider settings, historical exceptions, paused work or delivery controls.

Jev skip: Pete explicitly supplied the model and effort for every assignment;
there is no unresolved judgment that an advisory answer could change.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-OPENAI-MODEL-ROUTING-61-001",
  "plan_sha": "3edb24077cf36bcdeef8d9f270b24f0e32e491ab",
  "baseline": [
    {
      "command": "git grep -n -E 'Site management|Consequential independent|Routine bounded independent' HEAD -- docs/AI_MODEL_AND_ROLE_ROUTING.md",
      "exit_code": 0,
      "observation": "At b5812a6931210bb3ee2a94e8dea1c6bd467b3140 the current table names Astra Medium for site management, Astra High for consequential independent review, and combines routine independent review with High release execution; these differ from the owner-selected defaults."
    }
  ],
  "criteria": [
    {
      "id": "roles",
      "expected": "Eleven current OpenAI assignments use GPT-6.1 Sol with exactly the owner-selected Medium, High, Medium-or-High or Extra High efforts; every independent review is Extra High.",
      "verification": "Compare the current table's complete role-to-choice mapping with the eleven explicit assignments."
    },
    {
      "id": "preservation",
      "expected": "Routing text outside the current OpenAI routing table and its management-default sentence remains byte-identical to the accepted baseline; no product AI or delivery-control file changes.",
      "verification": "Normalize only the changed table/default span and compare to baseline; inspect the complete candidate changed-path set."
    },
    {
      "id": "decision",
      "expected": "Append one September 29 owner decision linked to the exact task and canonical routing standard, preserving all earlier decision bytes.",
      "verification": "Verify the old decision record remains an exact prefix and the new entry contains the selected model and owner reference."
    }
  ],
  "candidate_sha": "076069432b930a68ad69f543691d6823bdf9a0d6",
  "checks": [
    {
      "criterion_id": "roles",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "076069432b930a68ad69f543691d6823bdf9a0d6",
      "source_ref": "X:/PeerSlate/evidence/PS-OPENAI-MODEL-ROUTING-61-001/routing-verification.json",
      "observed": "All eleven assignments match Pete's exact model and effort choices."
    },
    {
      "criterion_id": "preservation",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "076069432b930a68ad69f543691d6823bdf9a0d6",
      "source_ref": "X:/PeerSlate/evidence/PS-OPENAI-MODEL-ROUTING-61-001/routing-verification.json",
      "observed": "Unrelated routing and test bytes are unchanged. The candidate changes only the two policy documents, their existing conformance expectations, and fixed acceptance evidence."
    },
    {
      "criterion_id": "decision",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "076069432b930a68ad69f543691d6823bdf9a0d6",
      "source_ref": "X:/PeerSlate/evidence/PS-OPENAI-MODEL-ROUTING-61-001/routing-verification.json",
      "observed": "One owner decision is appended with the exact session reference; all previous decision bytes are preserved."
    }
  ]
}
```

Writer self-review passed on the exact candidate above. All 31 governance
pointer tests passed. Ten outdated model expectations in the existing routing
test were aligned after the accepted surface extension; runtime verification,
inheritance and work-by-risk assertions remain intact. `git diff --check`
passed. Required Azure PR CI and accepted merge are still pending at this
receipt checkpoint. No runtime or deployment change is included.

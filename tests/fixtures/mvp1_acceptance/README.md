# G hands-on fixture

This is a local synthetic application, with real Flask routes, browser events,
bounded document parsing and image processing. Memory persistence, identity,
storage and AI/transcription transports are explicit substitutes. Restarting
clears the fixture. Nothing here proves SQL, real identities, provider quality,
distributed protections or physical-device behavior.

## Start the exact candidate

From the G worktree, use the configured development Python:

```powershell
$env:ANTHROPIC_API_KEY='test-key-for-ci-only'
& 'X:\PeerSlate\runtimes\development\Scripts\python.exe' -B -m tests.mvp1_acceptance_support --serve --require-sha <REVIEWED-CANDIDATE-SHA>
```

The launcher refuses a dirty or different checkout when `--require-sha` is
supplied. It prints its loopback URL and exact SHA. Open the printed fixture
chooser. Use separate browser contexts for member A, member B and guest.
No sign-in credentials or real account are needed. Keep the server running for
the entire review. Stop it with Ctrl+C afterward.

## Repeatable journey

1. Choose member A. In the shared composer, add one fictional role and two
   strengths; retain unfinished text while hiding/reopening the guide. Add
   explicitly, then reload and inspect the private receipt and records.
2. Attach `synthetic-resume.txt`, type another contribution, and optionally use
   a microphone with synthetic input. The configured transcription transport
   returns a fixed synthetic sentence. Review a proposal, correct its type and
   wording, save privately, then reload. Missing dates must remain unspecified.
3. Edit an existing Resume record and save the draft. Open publication review
   and private visitor AI. Select a source and ask a question. Confirm the
   answer reflects the saved draft; guest sharing must still be off.
4. Create and explicitly select a personal entry for My Story. Upload the
   synthetic photo from `tests/fixtures/resume_media/member-photo-1200x800.jpg`
   twice; check each scan, choose the two slots, swap/crop/preview and Add
   privately. Reload and verify saved selections before publishing.
5. Open `/app/profile`. Save a fictional introduction as `g-alex`, review and
   explicitly publish it. Open Resume publication review, choose display and
   visitor-AI permissions independently, review again and publish as `g-alex`.
6. In the guest context, read `/g-alex/resume`, inspect the chosen identity,
   words and images, ask six questions, and open a citation. Hidden AI-allowed
   information may support an answer, while display-only information may not.
7. In My Data, correct a shared fact; guest wording should update. Try publishing
   an older saved editor proposal and verify a conflict. Restrict permissions,
   stop sharing, delete a role plus its counted linked achievements, and restore
   privately. Check the guest context after each action.
8. In member B and guest contexts, attempt A's private source, citation and
   preview URLs. Inspect navigation, safe returns, clear recovery messages,
   keyboard focus, 320/390/768/1024/1440 widths and zoom/reflow.

The strict automated suite separately drives controlled response loss, blocked
provider/currentness changes, forged references, the 30-day recovery boundary,
cleanup failure/retry, cardinalities and independent Stage 07/09 fixtures.
Run `python scripts/run_mvp1_acceptance_browser_tests.py` using the same runtime
and a real `PEERSLATE_CHROME` executable. It fails on missing, changed or skipped
required cases. Its success does not replace the independent hands-on verdict.

## Review record

Record the actual candidate SHA, URL, synthetic boundaries, scenarios attempted,
passed and failed, reproducible defects, fixes independently retested, visual
correspondence and remaining limitations. Do not mark unattempted operations as
passed. The final review assignment supplies the exact frozen candidate; this
fixture document by itself is not a freeze, review receipt or acceptance.

## Three career-persona extension

For `PS-MVP1-THREE-PERSONA-ACCEPTANCE-001`, the same interactive server admits
three separate, initially empty synthetic owners: A for Riley Finch (early
graduate), B for Morgan Vale (mid career), and C for Casey Rowan (extensive
history). Selecting an account does not seed career content. Existing G test
setup remains explicit and unchanged.

The `personas/` bundle contains clearly fictional TXT inputs and an expected
fact manifest. Reupload the same base file for duplicate checks; use Morgan's
`conflicting-update.txt` for an unresolved start-date conflict, `empty.txt` for
empty input, and `unsupported-input.bin` for unsupported-file recovery. Do not
invent missing dates, convert the course certificate into a license, or treat
the career-stage differences as protected-trait assumptions.

This server's intake uses the deterministic uncertain/manual path, not a live
structured career extractor. Its visitor AI quotes supplied text. Same-process
save/reload/return is memory evidence; a restart clears all owners. Local
account selection does not qualify invited sign-in. Hosted SQL/provider,
physical-device and real-human onboarding timing remain separate. Observe
which Resume projection/template controls actually exist; this bundle adds no
production feature, template catalogue or visual direction.

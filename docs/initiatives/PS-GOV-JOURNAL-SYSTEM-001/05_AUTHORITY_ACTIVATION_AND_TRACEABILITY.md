# Authority Activation and Traceability

**Status:** In Progress — candidate authority and local verification complete;
Azure activation evidence pending

**Task branch:** `work/2026-07-20-journal-system-authority`

**Authoritative base:** `origin/main` at
`efd34335284d6c823d47cd7bac3cd2f901533612`

## What activates atomically

The package becomes current authority only when this complete change reaches
Azure `origin/main`. The atomic set includes:

1. Bible v2.8 and Roadmap v2.7;
2. current baseline, state, initiative, decision, document-control, handoff,
   agent, site-rule, Story, and AI-routing pointers;
3. detailed Journal, return-value, Ask Slate AI, messaging, public Ask [Name],
   legal-readiness, and active-lane transition records;
4. all three exact owner-supplied source DOCX binaries;
5. deterministic build sources and template/render/accessibility evidence; and
6. tests that fail if the pointer chain, binaries, hashes, package files, or
   critical architecture statements drift.

A local file or pushed task branch is reviewable evidence, not current
authority. The package is controlling across computers only after Azure records
the squash merge and the artifacts are present in `origin/main`.

## Binary traceability

| Role | File | SHA-256 |
|---|---|---|
| Bible template | `PeerSlate_Company_and_Product_Bible_v2.7.docx` | `CEEF99F1A84BF293217AD6D302A2B15E19B18104896DE7F8ED560416DEAF1836` |
| Bible output | `PeerSlate_Company_and_Product_Bible_v2.8.docx` | `47F9771C29A3FAEA18858865F402DF0E342840DAD80ECF4650B8ABCC537DE963` |
| Roadmap template | `PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.6.docx` | `7D615D3DFC2F463E25F86D166D6CEFE799D093D03AC64FE107B6FAAE026EDC4F` |
| Roadmap output | `PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.7.docx` | `899F0054483E886F79AACB4115AE0E160ACC44FA3BFFE5EEA2882A5C70EE6A83` |
| Supplied connected-site research | `source/1-PeerSlate-Hooks-and-Connected-Site-Research-Report-2.docx` | `1CF16A02A33A6B73BE13AD60361A4DDF3FFEF5D33C3F7CC7AF2B4EE54F4AA63F` |
| Supplied historical roadmap | `source/2-PeerSlate_Product_Strategy_and_Architecture_Roadmap_v2.5.docx` | `E9C8B8102C6416AC9739DA427726CF09907142F34082EA1930D621446EC003E6` |
| Supplied voice-first hooks research | `source/3-Deep-Research-Report-on-Hooks-for-a-Voice-First-Journaling-and-Growth-Website-2.docx` | `9C485B71906FB643D1F418478D21CA4C3E19A41B74C1FEF770A57437C76CFCE6` |

The supplied research is immutable provenance and an option library, not direct
user validation. Current requirements come from the owner decision record,
current Bible/Roadmap, and detailed initiative packages.

## Decision-to-record trace

| Owner decision | Constitutional record | Execution record |
|---|---|---|
| Capture anywhere, never a destination | Bible Appendix O | PS-JOURNAL files 01–02 |
| One Save Moment, one private canonical Moment, derived Journal | Bible Appendix O | PS-JOURNAL files 01–03 |
| Complete owner Journal and authorized curated projections | Bible Appendix O | PS-JOURNAL files 03–04 |
| Journal and My Story are distinct but share truth | Bible Appendix O | Story standard and PS-JOURNAL file 04 |
| Complete Use chooser plus finite shortcuts | Bible Appendix O | Roadmap Appendix H and PS-JOURNAL file 02 |
| Return, Momentum, prompts/rituals, Noticed, Mirror | Bible Appendix O | PS-RETURN-VALUE-001 |
| Ask Slate AI, Ask My Slate, Ask [Name] AI | Bible Appendix O | PS-ASK-SLATE-AI-001 and PS-ASK-PETE-AI-001 |
| Messaging committed but gated | Bible Appendix O | PS-MESSAGING-001 |
| Legal/site readiness starts early | Bible Appendix O | Early Legal and Site Readiness Standard |
| Home, Photo, and Projects cannot restore old assumptions | Roadmap Appendix H | file 04 active-lane transition |
| One manager, one writer, risk-based review | Roadmap Appendix H | AI Model and Role Routing |

The full requirement-ID allocation is in `01_SYSTEM_TRACEABILITY_MATRIX.md`.

## Azure release ledger

| Evidence | Current value before release |
|---|---|
| Task-branch source commit | Pending; cannot exist until the complete candidate is committed |
| Azure pull request | Pending; cannot exist before push |
| Squash merge commit | Pending; cannot exist before PR completion |
| Automatic pipeline / build number | Pending; cannot exist before the main merge |
| Build stage | Pending |
| Deploy stage | Pending |
| Live-route/auth-boundary smoke check | Pending |
| Deleted remote task branch | Pending |
| Authoritative remote-main tip | Pending |
| `git ls-tree origin/main` artifact proof | Pending |

Release hygiene completed before the candidate merge: obsolete duplicate
activation PR 115 (`work/2026-07-20-bible-v27-activation`) was set to
`abandoned`. PR 117 had already activated that older v2.7/v2.6 authority at
`efd34335284d6c823d47cd7bac3cd2f901533612`; leaving PR 115 active created a
credible stale-authority overwrite risk. Its source branch was preserved as
history and was not merged.

The post-activation closeout change replaces these pending values with exact
Azure evidence. Its own PR/pipeline is reported as terminal handoff evidence;
it does not create an infinite chain of self-referential closeout PRs.

## Runtime truth and deployment effect

This package changes governance and requirements only. It adds no application
route, schema, migration, service, feature flag, infrastructure setting, or
member-visible capability. Because the repository's main pipeline deploys on
all main changes, both the authority merge and its closeout will redeploy the
unchanged application bytes. Production smoke checks must therefore confirm
that public availability and signed-in authorization boundaries remain intact;
they must not claim the Journal architecture is implemented.

`application_behavior_commit` remains the last real application release rather
than being replaced by a documentation-only merge.

## Cross-computer retrieval states

1. **Local candidate:** available only in this worktree; not cross-computer
   authority.
2. **Pushed task branch:** remotely reviewable, but still not controlling.
3. **Merged Azure `origin/main`:** authoritative and retrievable from another
   clean checkout with `git fetch origin --prune` and `git pull --ff-only`.
4. **Public GitHub mirror:** intentionally not updated while
   `CURRENT_BASELINE.yaml` retains its explicit owner-approval hold. Private
   Azure `origin/main` is sufficient for the requested remote work.

## Rollback boundary

If the authority is later found defective, use a new governed task branch and
Azure PR that reverts or supersedes the exact merge while preserving evidence.
Do not edit a source binary in place, rewrite shared history, enable a feature,
or restore stale activation PR 115.

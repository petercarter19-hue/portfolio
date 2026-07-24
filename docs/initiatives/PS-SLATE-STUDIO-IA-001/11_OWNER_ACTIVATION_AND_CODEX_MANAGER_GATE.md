# PS-SLATE-STUDIO-IA-001 - Owner activation and Codex manager gate

## A. Decision and authority

- **Owner decision:** Pete explicitly activated Studio Slice 1 on 2026-07-24
  and directed the work through the designated-manager governance gate.
- **Owner role clarification:** when the work is running in Codex, the
  designated manager and downstream writer/reviewer roles are Codex roles.
  Claude Code, Claude Co-Work, Fable, Sonnet, and Opus are not dependencies for
  this Codex lane.
- **Designated manager:** the active ChatGPT Work/Codex manager task.
- **Package activated:** `PS-SLATE-STUDIO-SLICE-1-001`, limited to the
  protected Studio shell and Build Your Future frame in document 08 as amended
  by this gate.
- **Runtime entry status:** **manager-accepted, governance activation pending**.
  No runtime branch starts until the controlled governance change is merged to
  Azure `origin/main`.

Pete's decision supersedes the earlier package role chain that named
Claude/Fable/Sonnet/Opus surfaces. It does not change the one-manager,
one-writer, independent-review, evidence, visual-acceptance, Azure PR, or
production-verification requirements.

## B. Current authority verification

- Azure DevOps `origin` is authoritative.
- Verified `origin/main` before the gate:
  `a14033ca6e578fefa8ca43adaa2d49135417b165`.
- Direction branch before current-main reconciliation:
  `839e275a6d2fc512c5325d1d5334f13d3b0382e3`.
- Current-main reconciliation merge:
  `29d45267cc827fd39ac4fd9b1c52cac629a6678c`.
- The direction branch and Azure tracking branch matched before reconciliation.
- No unmerged remote branch changes the controlled Bible, Roadmap,
  `CURRENT_BASELINE.yaml`, `CURRENT_STATE.md`, or
  `ACTIVE_INITIATIVES.md`.
- Other local worktrees were inspected read-only. Their branches are already
  merged/deleted remotely or outside this package. The unrelated untracked
  archive in `portfolio-claude-review` remains preserved.

## C. Current product and route evidence

- Production `GET /app` returns the existing safe sign-in redirect.
- Production `GET /app/studio/build-your-future` returns `404`.
- The current public `/interview-studio` remains live, public, and
  browser-local under its existing truth boundary.
- Current `origin/main` now contains the released flag-off Owner Home, private
  Journal J1 frontend, Community tabs, authentication callback hardening, and
  identity-storage wake-up handling. None is Build Your Future implementation.
- The new Studio route must not replace, reimplement, or silently alter those
  surfaces.

## D. Manager review result

The manager reviewed documents 06 through 10, the accepted visual manifest,
the current Bible and Roadmap named by `CURRENT_BASELINE.yaml`, the current
governance records, the affected routes, and current-main application boundaries.

**Result: Pass for controlled governance activation; Conditional for runtime
entry until the governance PR merges.**

Accepted decisions:

1. `/app` remains the protected Workshop entry.
2. `/app/studio/build-your-future` is the bounded Slice 1 route.
3. Workshop, Build Your Future, and the current public Interview Studio remain
   distinct and truthfully labeled.
4. Journal remains canonical infrastructure and the complete private
   chronology; Studio becomes the work-first experiential center. Studio does
   not create a competing fact store or replace Save Moment, derived Journal
   membership, or exact-reference projections.
5. Slice 1 proves only the protected shell/frame, navigation, private and
   published-Slate status, and truthful states.
6. Board content/persistence, editing, experiments, Ask Slate, practice
   grounding, publishing, Interview Studio rename/restructure, Community pulse,
   and public-page alignment remain excluded.
7. The owner-accepted responsive/state image set is the visual direction.
   Runtime implementation must still prove the real browser, authorization,
   accessibility, responsive, and failure contracts.

## E. Current-main correction to document 08

Document 08 was written before the current authentication and owner-shell
releases. The following correction is controlling:

- `app.py` is writable only for the bounded default-off
  `PEERSLATE_SLATE_STUDIO_SLICE1_ENABLED` configuration entry.
- `auth_routes.py` is writable only for the protected route, flag boundary,
  server-derived frame view model, safe sign-in return, and private/no-store
  response.
- Existing `/app`, Owner Home, Journal, Community, Capture, public Interview
  Studio, shared services, schema, migrations, and deployment configuration
  remain forbidden.
- No new API, service, database dependency, migration, storage layer, or
  JavaScript state store is authorized.

If the writer cannot implement the slice inside that boundary, it stops and
returns the conflict to the manager.

## F. Controlled governance reservation

The Codex manager reserves the following files only for the activation change:

- `docs/governance/CURRENT_BASELINE.yaml`;
- `docs/governance/CURRENT_STATE.md`;
- `docs/governance/ACTIVE_INITIATIVES.md`;
- the next controlled Bible and Roadmap versions derived from v2.8/v2.7;
- `docs/governance/DOCUMENT_CONTROL.md`;
- `tests/test_governance_pointers.py`; and
- this initiative package.

The activation change must preserve the one-Journal constitutional model while
recording the work-first Studio relationship:

> Journal preserves canonical member history. Slate Studio is the private
> experiential workspace where members build, practice, explore, and shape
> possible futures. The public Slate presents approved output, and Community
> connects selected output.

No application behavior is changed by the governance activation.

## G. Codex delivery roles after governance

- **Architect/manager:** this ChatGPT Work/Codex task only if a materially new
  architecture question appears; the accepted Slice 1 package is not
  re-architected by default.
- **Sole implementation writer:** one bounded central Terra writer on a fresh
  branch from the exact post-governance `origin/main`; it tests and self-reviews
  the complete diff.
- **Independent reviewer:** one fresh central Sol High review-only task at the
  exact pushed implementation SHA. This review is mandatory because the
  protected slice includes identity, authorization, private server-derived data,
  and a default-off exposure boundary.
- **Corrections:** the same implementation writer corrects accepted findings and
  reruns affected evidence.
- **Visual/product acceptance:** Pete gives final visual acceptance on the
  corrected candidate; the Codex manager confirms scope/product readiness before
  the implementation PR.
- **Release/closeout:** the accepted writer completes Azure PR, pipeline, and
  production verification under manager oversight.

No second writer may edit the implementation branch.

## H. Stop conditions

Stop and return to Pete/manager if:

- a current writer reserves any controlled governance or proposed runtime file;
- the controlled Bible/Roadmap change weakens Journal, privacy, canonical
  Moment, authorization-before-retrieval, AI-proposal, or publication rules;
- current-main changes make the isolated route-local shell impossible;
- the writer needs a schema, service, migration, infrastructure, public-page,
  or existing Owner Home/Journal/Interview change;
- the visual authority cannot be met truthfully or accessibly; or
- Azure `main`, pipeline, or production evidence contradicts the package.

## I. Single next action

Complete and merge the controlled governance activation. Then create the
separate Slice 1 implementation branch from that exact Azure `origin/main` and
dispatch the sole Codex writer.

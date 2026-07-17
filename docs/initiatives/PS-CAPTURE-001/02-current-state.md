# Current state before implementation

## Repository and delivery baseline

- Azure DevOps remote `origin` and `origin/main` are authoritative.
- GitHub is a non-deploying backup mirror.
- The package began from Settings squash merge
  `086753f2e1df2fb02dfd55a51d41b35d12fcc431` in an isolated worktree.
- The original checkout contains unrelated user-owned artifacts and is not used
  for this branch.

## Relevant application state

- `owner_routes.py` already protects `/app/settings` with
  `get_current_identity()` and a controlled unavailable state.
- `identity.py` derives trusted identity server-side and persists/loads the
  opaque `user_key`; auth internals are outside this package.
- `services/database_service.py` executes only explicitly allowlisted stored
  procedures using bound parameters.
- `templates/owner_workspace.html` provides the signed-in owner launch surface.
- `static/css/owner-app.css` provides the owner-workspace visual foundation.

## Relevant data state

- `PS-AUTH-001` provides `app_users`, `user_identities`, and one private
  `member_profiles` row per user.
- No canonical `captures` table or capture read/write procedure exists.
- `voice_drafts` and `file_assets` exist for different future workflows and are
  not reused as the canonical text-capture record.
- Existing pages contain fixture and specialized content, but none provides a
  real owner-isolated Universal Capture intake.

## Defects and constraints found during review

- The onboarding brief typed `@UserKey` as `uniqueidentifier`; the actual
  application contract is opaque `nvarchar(300)` and must be followed.
- The database allowlist did not include capture procedures.
- The deployment runbook referred to the retired `azure` remote and did not
  support applying one approved optional migration safely.
- Route mocks alone cannot prove two-user SQL isolation, so a transactional
  synthetic-owner verification is required.
- Flask flash messaging would add session-secret infrastructure solely for this
  slice; fixed query-state messages provide the required redirect feedback
  without that dependency.

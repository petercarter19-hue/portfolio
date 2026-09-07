# Navigation and route-truth completion record

## Outcome

Package `PS-PUBLIC-NAV-ROUTE-TRUTH-002` delivers the approved nonvisual
navigation correction. Shared navigation is now generated from the same
server declaration that validates sign-in returns. Capture, Slate Board, and
Workshop are no longer promoted, while their runtime and saved-content paths
remain available for compatible direct links. `/app` stays the neutral member
fallback; My Story and the canonical Feed at `/the-slate` remain available.

The four held preview routes and their referring template/card and sitemap
behavior are unchanged. The package does not claim final member Profile,
Journal, Projects, legal/trust destinations, deployment, or production proof.

## Candidate and review

- Branch: `work/2026-09-06-public-nav-route-truth-002`
- Activated base: `c86af0d2ed1da057a6a052c0dd9ef8d69f9f3218`
- Claim-extension base: `11fad4a9b6a58bb5133acdbbc4d5316bc5f36c66`
- Final candidate SHA: the immutable commit containing this record; recorded
  in the independent review receipt and merge preflight
- Independent exact-SHA review: required and pending
- Production authority: withheld

## Verification

The focused source matrix runs in fresh legacy and V2 Opportunity processes
with `PYTHON_DOTENV_DISABLED=1`, a fixed placeholder provider key, and the
existing portfolio virtual environment. No external provider or member
database is configured.

- Pre-correction candidate `460035b5fa37492bdb976c8fc153a6e234abf1de`,
  legacy Opportunity process: **176 total: 173 passed, 3 intentional skips**.
- The same pre-correction candidate in the V2 Opportunity process: **176
  passed**.
- The package-specific route-truth suite within those runs contributes 11
  passing tests in each fresh process.
- After the review correction, the affected route-truth and sign-in-return
  suites pass in fresh legacy (**43 total: 40 passed, 3 intentional skips**)
  and V2 (**43 passed**) processes.

Initial synthetic browser evidence passed:

- member `/app` in legacy and V2 startup configurations;
- signed-out `/petec/resume` and `/petec/my-story`;
- 320, 390, 768, and 1280 CSS-pixel viewport checks with no scoped horizontal
  overflow;
- mobile Menu parity, accessible labels, keyboard Escape and focus recovery,
  account-menu keyboard access, search results, reduced-motion preference, and
  a real JavaScript-disabled no-script render;
- Opportunity Slate naming and absence of Capture, Slate Board, and Workshop
  from the checked navigation representations;
- corrected `/` metadata and My Story/Résumé destinations, corrected
  `/experience` My Story destinations, and no scoped horizontal overflow at
  390 CSS pixels; and
- a restarted V2 `/app` with the accurate four member cards and private-ingress
  copy under the normal local synthetic session-probe configuration.

The in-app browser did not expose a reliable way to prove genuine browser
200%/400% zoom. The responsive viewport checks are not presented as zoom proof.
The browser fixture compared the following frozen source bytes:

| Path | SHA-256 |
|---|---|
| `safe_return.py` | `d5dbd15e16a8864ae105d9aab71bca939626077468d50fc68637a0d3e84c7615` |
| `app.py` | `cfc9e91d2cc5d886a7614f16f87bb239333bd25f9808133d5adbc0b6d0890e64` |
| `templates/base.html` | `98b4e3cea57521fb98f3d4d58768a09537da8c8aca7747f3e5ea794fefd17fbe` |
| `templates/owner_workspace.html` | `ef2754c77135cad506d39a9d85eb0a6a2b8796908918b387e076bcb3f23ee21e` |
| `templates/partials/profile_tabs.html` | `d43aed067ceb665b4c2cc960eedc81aa59767c9e6a162a93c436bf856711fd82` |
| `templates/partials/homepage/_voice_hero.html` | `f46eabf7e50882a8d1936b6dc312274c9bce626535e4b820f7fe61982d651bb2` |
| `templates/homepage.html` | `8ef18e7e147fb5436b8f8b50fe0d1693e14d225a6176b43503e9b999e1a20351` |
| `templates/partials/homepage/_story_future_scene.html` | `a29523513bfbeb20e8f10bcf68d9b319c2b6c9812e5aa0879177e83b6372f655` |
| `templates/experience.html` | `c2f8a1fbc315e8d8d11a601f3987464ab0650c249002ee5b8f5f9480ebb75e20` |

The `safe_return.py` hash was refreshed after the rendered checks for
non-rendered corrections: exact endpoint identities on opaque Capture photo
reads, exact disabled-value handling for Interview video/history returns, and
restored exact Workshop work/session landings with safe-parent handling for
review/reset leaves. They change only safe parent/fallback resolution and do
not change a rendered destination. Focused coverage passes in both legacy and
V2 processes.

Final candidate binding and independent review remain release-coordination
steps after this writer freeze. The synthetic browser processes were stopped
after evidence collection; no local synthetic runtime remains active.

## Compatibility and privacy

- Ordinary page headers continue to omit arbitrary query strings from sign-in
  return links.
- Private route prefixes remain protected independently of which products are
  visible in navigation, including cache and back-forward-cache protections.
- Exact route and endpoint checks prevent an arbitrary registered GET or a
  mutation/API route from becoming a return destination.
- Opaque export, capture, Workshop, Community, and Opportunity action URLs
  return to declared safe parents without reflecting their keys.
- Caller defaults are validated; a disabled or unregistered default terminates
  at `/app`.
- Feature removal is promotional only. No storage, route module, schema, voice
  input, onboarding, or member data is deleted or migrated.

## Rollback

The implementation is source-only and runtime-inert until a separately
authorized deployment. Reverting its eventual squash merge restores the prior
navigation and safe-return behavior. There is no data, schema, identity,
provider, flag, or infrastructure operation to unwind.

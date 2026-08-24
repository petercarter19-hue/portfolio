# PS-SETTINGS-MY-DATA-SHELL-001 — truthful Settings and My Data shell

**Slice:** A only
**State:** Active implementation package
**Delivery path:** Protected
**Claim:** `docs/governance/lane_claims/PS-SETTINGS-MY-DATA-SHELL-001.json`
**Repository authority:** Through accepted merge under the active claim
**Production authority:** Withheld; deployment is a separate exact-main-SHA operation

## Outcome

Extend the existing authenticated `/app/settings` page with a truthful,
read-only My Data summary for every signed-in member. Preserve the established
PeerSlate page composition and visual system while correcting the nested main
landmark, duplicate `main-content` ID, and owner-era user-facing wording.

This package does not make Settings a dashboard or introduce a new visual
language. It keeps the existing route, server-derived identity, identity
failure fallback, Back to workspace link, and POST sign-out behavior.

## Product truth

- `/app/settings` remains authentication-protected. Any signed-in member may
  view the page; identity is resolved on the server.
- Display name, email, and signed-in state are current account facts.
- Private by default is a current PeerSlate product rule, not a stored member
  preference.
- Member-created records remain managed in their existing product areas using
  only the item-level actions those areas already provide.
- Preferences and consents are upcoming. No control appears before real
  behavior exists.
- Account-wide export, deletion, and closure are not available today.
- A consolidated retention schedule and complete-erasure promise covering
  backups and provider processing are not yet resolved.

## Mutable implementation surfaces

- `docs/governance/PACKAGE_REGISTRY.json`
- `docs/initiatives/PS-SETTINGS-MY-DATA-SHELL-001/README.md`
- `templates/owner_settings.html`
- `static/css/owner-app.css`
- `tests/test_owner_settings.py`

The package-reserved claim, review receipt, and runtime-inert evidence paths
remain untouched until their respective lifecycle and independent-review
steps.

## Acceptance contract

1. The initiative is represented exactly once in the package registry under
   `current_protect`, with accurate category and total counts.
2. The rendered Settings page has exactly one `main` landmark, one
   `id="main-content"`, and one matching skip-link target.
3. Member-facing copy uses member language and explains Private by default as
   a product rule rather than a saved setting.
4. My Data visibly distinguishes Current, Upcoming, Not available today, and
   Not yet resolved states without presenting any control in that section.
5. No route, navigation destination, client script, field, toggle, schema,
   service, account-wide operation, or second canonical data store is added.
6. The page continues to work without JavaScript and preserves the existing
   navigation and POST sign-out controls.
7. Existing identity failure behavior returns an unavailable response without
   disclosing member data.
8. Scoped CSS supports narrow-screen reflow and wrapping of long identity or
   status values using existing tokens and presentation patterns.

## Deferred child packages

The remaining Settings and My Data program stays inactive and separately
governed: real preferences and consents; versioned owner-scoped account export;
retention presentation after an accepted schedule; deletion propagation; and
reauthenticated account closure. This Slice A claim grants no authority to
start or combine those outcomes.

## Review, rollback, and proof boundary

The writer runs focused Settings, authentication/shell, registry, and
governance checks and performs one complete-diff self-review. Because this is a
Protected identity/privacy surface, an independent reviewer must pass the
exact immutable pushed candidate before any review receipt, merge admission,
or PR completion.

Rollback is a repository revert of this package's template, CSS, test,
initiative, and registry bytes. There is no schema or data rollback. A PR,
merge, deployment, live release identity, and live authenticated behavior are
separate states and must not be inferred from the implementation candidate.

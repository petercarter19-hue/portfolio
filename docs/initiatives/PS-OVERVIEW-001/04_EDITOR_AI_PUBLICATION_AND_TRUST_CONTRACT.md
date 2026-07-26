# Editor, AI, publication, and trust contract

## 1. Core editing promise

The authenticated member edits a private structured Overview draft. The public
Overview changes only after the member previews and explicitly publishes a
valid complete revision.

Manual composition is complete without AI. AI is an optional proposal path
inside the same composer.

## 2. Authorized entry and representations

- The server derives member identity and owner permission from the authenticated
  session.
- A client flag, hidden button, route parameter, profile slug, or submitted
  owner ID never grants access.
- Authorization occurs before draft, source, media, or version retrieval.
- Public and editor surfaces may share internal rendering rules, but they do
  not share the same response payload.
- The public representation contains only the published, audience-authorized
  projection. It excludes draft content, source diagnostics, private record
  names, AI proposal metadata, hidden blocks, version history, and edit
  controls.
- Edit controls use semantic buttons and inputs and remain reachable by
  keyboard and touch. Hover-only affordances are prohibited.

## 3. Starting paths

The editor offers three equal choices:

1. **Build from my résumé** — propose/select eligible records and a sensible
   block outline without publishing.
2. **Build it myself** — start with a blank structured draft or add blocks
   manually.
3. **Let AI propose a draft** — create a source-grounded private proposal that
   lands in the same editor for review.

None is labeled as the only recommended way. A member can move freely from one
path to another without losing accepted draft work.

## 4. Owner workflow

1. Open **Edit Overview**.
2. Create or continue the private draft.
3. Select Story & Career or Work & Impact.
4. Add a supported block from the catalog.
5. Select eligible source records and/or write bounded projection copy.
6. Choose Feature, Standard, or Compact emphasis where allowed.
7. Add eligible media, focal point, alt text, consent/provenance state, and
   audience.
8. Choose one truthful public destination or keep the block honestly static.
9. Reorder blocks with drag and keyboard/structured move controls.
10. Hide/show blocks without deleting source records.
11. Resolve readiness warnings and blockers.
12. Preview the exact visitor representation at desktop, mobile, large-text,
    and relevant audience states.
13. Save/allow private autosave.
14. Explicitly publish the complete validated revision.
15. Restore a prior publication only after preview and explicit confirmation.
16. Explicitly **Unpublish Overview** when the member wants the existing résumé
    Summary to become the public opening again.

## 5. Draft and version states

| State | Meaning | Public effect |
| --- | --- | --- |
| No draft | No in-progress composition | Existing publication remains or résumé begins directly |
| Draft saving | Private changes are being persisted | None |
| Draft saved | Current private revision is durable | None |
| Draft save failed | Local view has changes not yet confirmed by server | None; clear retry/recovery required |
| AI proposal pending | Optional scoped proposal is processing | None |
| AI proposal ready | Proposed changes await member decision | None |
| Preview | Public representation of an exact draft revision/audience | None |
| Ready to publish | All blocking validators pass for the exact revision | None |
| Publishing | Atomic server operation in progress | Prior publication stays active until success |
| Published | Exact reviewed revision becomes current | Public changes atomically |
| Publish failed | New revision did not become current | Prior publication remains active |
| Benign source evolution | A selected still-eligible source gained or changed context without invalidating the exact published facts | Existing publication may remain pinned; new publish requires review |
| Corrective source supersession | The prior source/version or claim is marked inaccurate/invalid | Affected public claim or block fails closed immediately; no corrected wording is auto-published |
| Source unavailable | Source deleted, revoked, or no longer eligible | Public output fails closed according to block contract |
| Restored | A prior publication was previewed and republished as a new current revision | Public changes atomically with preserved history |
| Unpublishing | Authorized atomic withdrawal is in progress | Current publication remains until success |
| Unpublished | No current public Overview; history and private draft follow policy | Existing résumé Summary becomes the public opening |
| Unpublish failed/conflicted | Withdrawal did not complete | Current publication remains active; owner receives retry/conflict choices |

Draft autosave and publication are separate operations. Autosave never broadens
an audience or changes the public page.

## 6. Readiness validation

### Blocking

- unauthorized or nonpublic source for the selected audience;
- benign source evolution selected for the next publication requires member
  review;
- corrective source supersession not yet acknowledged/replaced in the draft;
- missing required field;
- text or item count exceeds an accepted hard limit;
- missing alt text when the media conveys meaning;
- missing consent/provenance classification;
- destination missing, private, or invalid when the block claims an action;
- unsupported block/style/emphasis combination;
- style switch would leave selected content undisplayed without an explicit
  member decision;
- stale draft revision or publication concurrency conflict; or
- unresolved AI proposal inserted without the required member decision state.

### Warning

- approaching a content budget;
- repeated claim or destination;
- unusually long Overview;
- selected records may be stronger in another order;
- media crop may weaken at a supported breakpoint;
- an optional source relationship is unconfirmed; or
- a style would present the same content more effectively.

Warnings explain the tradeoff and leave the final truthful choice to the
member. Blockers identify an exact fix and never ask the member to guess.

## 7. Reordering and visual control

- Drag-and-drop is optional convenience.
- Every reorder action has Move up, Move down, and Move to position
  equivalents.
- Keyboard focus remains understandable after a move and the new position is
  announced.
- Reordering changes semantic order, not just CSS placement.
- Emphasis options are finite and previewable.
- The system may prevent an invalid emphasis combination rather than producing
  a broken public page.
- A member cannot freely resize, overlap, layer, or position Overview blocks.
  Those richer spatial Story controls belong to the separate Story Composer,
  not this concise Overview.

## 8. AI may do

AI may, from explicitly eligible selected context:

- draft an Executive Brief, Story Spotlight, capability summary, or future
  statement;
- propose a complete private Overview outline;
- suggest Story & Career or Work & Impact and explain why;
- suggest eligible roles, outcomes, skills, Story chapters, and order;
- cluster selected records into a capability or specialty spotlight;
- shorten or clarify projection wording;
- identify repetition;
- preserve an exact metric value that the member typed in the metric field or
  explicitly supplied in the current request;
- propose or shorten a metric label while treating its value as immutable; and
- ask a focused question when the source does not support a truthful proposal.

## 9. AI may not do

AI may not:

- invent or embellish employers, roles, dates, degrees, certifications, awards,
  skills, projects, outcomes, scale, money, percentages, team counts, or
  personal history;
- retrieve, insert, infer, calculate, round, embellish, change, or silently
  substitute a metric value the member did not explicitly supply;
- retrieve records the member is not authorized to use;
- turn private Journal or Goal content into a public block automatically;
- mutate canonical résumé, Story, Journal, Project, or profile facts;
- select or broaden an audience;
- switch the published style;
- save over accepted wording without an explicit comparison/decision;
- mark a proposal as member-authored merely because it was generated;
- choose media consent or provenance on the member's behalf;
- publish, restore, withdraw, or delete; or
- conceal its supporting sources or uncertainty.

## 10. AI proposal interaction

Each proposal shows:

- the requested task;
- the exact eligible source records/versions used where the task is
  source-grounded;
- the proposed text, selection, order, or style change;
- a before/after comparison when replacing existing draft content;
- uncertainty or missing evidence;
- **Accept into draft**, **Edit**, and **Reject** actions; and
- a clear statement that no public change has occurred.

Accepting a proposal inserts it into the private draft with proposal lineage.
Source references remain visible for source-grounded tasks. First-release proof
metrics have no metric-source or provenance-state system; their exact value is
member-supplied and remains locked during AI label editing. The member may edit
the draft. It becomes published projection wording only through the normal
preview and explicit whole-Overview publication.

If AI is unavailable, times out, or returns invalid output, the current draft
is preserved and the complete manual workflow remains available.

## 11. Metrics and credibility

Pete approved a deliberately simple first-release metric model:

- a proof metric is optional authored Overview projection content;
- the member supplies the exact displayed value directly or explicitly in the
  current AI request;
- AI may preserve the exact value and help format or shorten the label;
- AI may not invent, retrieve, infer, calculate, round, embellish, alter, or
  silently substitute the value;
- the metric passes through normal owner draft, exact preview, and explicit
  whole-Overview publication; and
- the product makes no PeerSlate-verified or source-backed claim about it.

There is no first-release metric source selector, evidence attachment,
verification badge, or sourced/member-confirmed/unsupported provenance state.
The member can edit, hide, reorder, or remove a metric. If AI receives no exact
member-supplied value, it leaves the value unchanged and asks for one.

Source-backed proof metrics are deferred until the basic system has been
implemented and reviewed live. A future enhancement requires a new product
decision, migration treatment for existing authored metrics, privacy and
authorization rules, UX states, tests, and visual acceptance.

## 12. Media, privacy, and truth

- Media is optional in every block except when a future exact visual explicitly
  makes a member-selected item required for that chosen block.
- The member selects the media and its audience.
- Meaningful media requires alt text; decorative system treatment is marked
  decorative and does not repeat adjacent text.
- The member controls crop/focal point within approved responsive treatments.
- Media containing other identifiable people requires an explicit applicable
  consent/rights confirmation.
- Generated or stock imagery must be labeled and cannot be presented as proof
  of the member's workplace, team, family, project, or accomplishment.
- Removing, withdrawing, or narrowing media access removes it from the public
  block and invokes the approved text-led reflow.
- Raw private uploads and source files are never exposed merely because a
  projection references them.

## 13. Story and Journal boundary

- A Story Spotlight or Story Chapters preview may use only an eligible
  explicitly published Story projection for the same audience. A Story
  Spotlight may add a bounded member-authored teaser only when it remains
  grounded in that selected projection.
- Standalone member-authored career origin, personal context, philosophy, or
  future wording uses a Flexible Spotlight with a truthful title. It is not
  labeled a Story Spotlight and receives no **Read my story** destination unless
  an eligible same-audience published Story exists.
- Saving a private Moment or adding it to Journal never adds it to Overview.
- Private Journal is not queried for public rendering.
- Removing an item from Overview does not remove it from Story, Journal,
  résumé, Work, or Projects.
- Removing an item from Story or narrowing its audience invalidates the
  corresponding public Overview reference.
- Current `/petec/my-story` behavior remains fixture-driven; this package does
  not represent Story Composer as live.

## 14. Publication transaction

The future publication operation must:

1. authorize the owner and target profile;
2. require the exact current draft revision to prevent lost updates;
3. validate every applicable selected source, destination, media item,
   audience, and style/block definition, plus the authored proof-metric field
   contract without requiring metric provenance;
4. generate the exact public representation for preview parity;
5. pin the style definition/version, block definitions, source/projection
   versions, order, emphasis, media focal data, and audience result;
6. write one complete published revision or no revision;
7. retain the prior publication for restore/audit according to policy;
8. record the actor, time, and revision relationship; and
9. invalidate/update public caches only after success.

The client cannot assemble a trustworthy publication by posting arbitrary
rendered HTML.

## 15. Corrective source propagation

The source system or projection contract must distinguish:

- **Benign evolution:** new context or a changed record version that does not
  invalidate the exact facts pinned in the public claim. The current
  publication may remain stable; the draft is marked for review before it can
  publish against the new source.
- **Corrective supersession:** the member or governed lifecycle marks the prior
  fact/version as inaccurate, invalid, revoked, or unsafe to continue
  presenting. The public resolver immediately omits the affected claim or its
  entire block according to the block contract, invalidates affected caches,
  and records the owner-visible reason. It never substitutes corrected
  language automatically.

The owner reviews the corrected source and explicitly publishes a replacement.
If the public result cannot remain coherent after omission, the whole Overview
fails closed to the existing Summary fallback until the owner republishes.

## 16. Unpublish transaction

The owner-controlled unpublish operation must:

1. authorize the owner/profile and exact current publication revision;
2. show the exact result: Overview removed, current résumé Summary restored as
   the opening, detailed résumé unchanged;
3. require explicit confirmation;
4. use concurrency protection so a stale editor cannot withdraw a newer
   publication unknowingly;
5. atomically clear the current-publication pointer or apply the equivalent
   governed withdrawal state;
6. retain publication and audit history;
7. preserve or discard the private draft only according to a separate explicit
   member choice/policy;
8. invalidate public caches only after success; and
9. leave the current publication unchanged on failure.

Unpublish is not delete. A later restore revalidates current source, media,
destination, and audience eligibility and creates a new publication revision.

## 17. Concurrency and restore

- Draft writes use revision checks or an equivalent conflict contract.
- A stale editor never silently overwrites a newer draft or publication.
- Conflict handling identifies what changed and preserves both recoverable
  versions until the member decides.
- Restore previews a prior publication against current authorization and
  source eligibility.
- Restore creates a new revision; it does not erase audit history.
- A revoked/private source remains ineligible even if an older publication once
  contained it.
- Publish, unpublish, and restore all compare the expected current publication
  revision and fail safely on conflict.

## 18. Failure and unavailable behavior

| Failure | Required behavior |
| --- | --- |
| Draft save unavailable | Preserve current work locally when safe, explain unconfirmed state, offer retry/export or recovery |
| AI unavailable | Keep draft intact; return to manual editor |
| Preview generation fails | Do not publish; keep prior public revision |
| Destination validation fails | Identify exact block/action; block publish or render static as defined |
| Source authorization fails | Do not return private source data; fail closed |
| Media unavailable | Use approved text-led state when valid; otherwise block publish |
| Publish conflict | Keep public revision unchanged; show conflict and refresh choices |
| Publish transaction fails | Keep prior public revision; no partial update |
| Unpublish conflict/failure | Keep current Overview public; show exact conflict/retry state |
| Corrective source supersession | Remove the invalid public claim/block immediately, invalidate affected caches, and require owner review for replacement |
| Corrective omission makes Overview incoherent | Fail closed to the existing Summary fallback; retain owner-visible recovery path |
| Public renderer cannot load optional media | Preserve text/meaning; no broken empty slot |
| Entire Overview unavailable | Preserve truthful résumé access when safely possible; never expose a draft fallback |

## 19. First-release audience

Pete approved one first-release rule: the Overview inherits the public résumé
audience and cannot be broader. Individual blocks may be narrower only by
omission from that public publication.

A separately selectable Overview audience is a later-capable enhancement and
requires its own product, preview, authorization, test, and visual decisions.

The system must never infer that public résumé visibility automatically makes
private Story, Journal, Goal, media, or source evidence public.

# Member Overview page-purpose and non-redundancy inventory

This record follows
`docs/templates/PAGE_PURPOSE_AND_NON_REDUNDANCY_INVENTORY.md`. Pete approved it
for the production-intent visual-creation gate on 2026-07-26.

## A. Scope and approval

- **Initiative / slice:** `PS-OVERVIEW-001`
- **Page or surface:** Configurable Overview above the full public résumé
- **Member need this page serves:** Give a visitor a concise, credible, human,
  and navigable orientation to the member without repeating the full résumé
- **Named capability and visual authority status:** One Overview system; Story &
  Career flagship and Work & Impact alternate. Supplied concepts are direction
  inputs only; no production visual authority is locked.
- **Known source / capability limits:** Current public résumé is live and
  fixture/data-driven. Current public My Story is a fixed fixture projection.
  Authenticated multi-user Overview composition, publication records, and style
  rendering do not exist.
- **Prepared by / date:** Codex, 2026-07-25
- **Pete inventory approval / date:** Approved, 2026-07-26
- **Inventory status:** Owner-approved for visual creation; exact visual
  authority remains pending

## B. Meaningful public item decisions

### B1. Shared shell and page boundary

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Current résumé section ribbon | Orient the visitor among sections on `/petec/resume` | Existing right-side control; first entry is currently Summary | Stable same-page anchors and focus | Public destinations only; no hidden-section link | Current page-depth control outside the center canvas | Keep / update first entry | Overview must replace a weaker opening, not add a second navigation layer |
| Future left Context Rail | Approved target pattern for the résumé, not current implementation | `OWNER_CONTEXT_RAIL_STANDARD.md`; adoption/migration needs its own package and visual acceptance | Same local section destinations only | Public sections only | Future replacement for the current ribbon | Defer implementation | Pete's left-rail direction is preserved without misrepresenting it as live or authorized here |
| Overview / Summary first section entry | Reach the opening that actually renders | Derived from publication state | Published: **Overview** → `#overview`; no publication: **Summary** → `#summary`; existing `#summary` and `#resume-overview` aliases reach the absorbed opening | Public; exactly one first entry | Prevents duplicate Overview and Summary destinations | Keep / change dynamically | One opening, one contextual destination |
| Existing Summary opening | Provide portrait, identity, positioning, intro, actions, and public Ask panel today | Existing live `/petec/resume` region | Existing Summary/Ask/Resume/Contact behavior | Public approved résumé data | Fallback opening when no Overview is published | Combine / fallback | A published Overview absorbs this job; it must not render a second hero |
| Ask [Name] AI public entry/panel | Let visitors explore approved public history | Existing public-only grounded Ask capability | One shared contextual action opens/uses the approved panel | Public sources only; no private Slate retrieval | Distinct interactive exploration, not identity copy | Keep in shared context | Do not duplicate it in the hero; mobile may use one compact accessible shared-actions menu |
| Résumé PDF action | Let the visitor obtain the existing résumé document | Existing public PDF path | One shared contextual action opens/downloads the approved PDF | Public | Document action | Keep in shared context | Do not duplicate it in the hero or throughout Overview |
| Résumé begins here boundary | Tell the visitor that concise orientation ends and the detailed résumé starts | System-owned label, not member copy | May be a heading/landmark; no required action | Public when Overview renders | Separates the absorbed opening from Impact, Skills, Experience, and Credentials | Keep | Replaces the mockups' duplicate Full Résumé block |
| Full Résumé summary shown in concepts | Preview the résumé again | Duplicates the actual résumé immediately below | Repeated download/print actions | Public duplication | No unique job | Remove | Pete directed that the real résumé starts there |
| Concept top navigation | Move among concept sections | Illustrative concept chrome | Duplicates site navigation/rail | Public if implemented | No unique job in Overview | Remove | Do not establish a new navigation layer |
| Concept footer/contact repetition | Repeat contact and legal actions | Illustrative concept chrome | Duplicates shared shell/contact | Public if implemented | No unique Overview job | Remove / use shared shell | Avoid repeated calls to action and shell drift |

### B2. Shared Overview content

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Identity hero | Establish who the member is and the primary professional promise | Public profile identity plus approved projection copy | Optional one primary and one secondary action | Published public projection; profile privacy rules apply | Fastest orientation on the page | Keep | Required for a coherent Overview |
| Portrait | Add recognition and human presence | Member-selected eligible media | No action by default | Optional; audience, consent, alt/decorative state, crop, and withdrawal governed | Identity media, not evidence of work | Keep optional | Text-led hero must work without it |
| Professional headline | State role, direction, or professional identity | Member-authored/accepted projection; may reference current role | Static unless paired with a precise destination | Public published wording | One concise positioning statement | Keep | Needed in both styles |
| Intro / bottom-line statement | Explain value and focus in a few sentences | Member-authored or accepted source-grounded projection | Optional destination when the statement has fuller public context | Public published wording with revision history | Connects identity to proof | Keep | Replaces long summary duplication |
| Location/contact items | Let eligible visitors understand location or connect | Approved public profile fields | Specific `mailto`, LinkedIn, contact, or approved route | Individually audience-controlled; never expose private contact data | Practical contact context | Keep optional | Maximum and visibility rules prevent clutter |
| Primary hero action | Offer the best next step | Existing eligible contact destination | **Connect** | Public and validated | One dominant relationship action | Keep | Owner-approved hero primary; shared Download PDF and Ask [Name] AI stay outside the hero |
| Secondary hero action | Move directly to the detailed record below | Stable same-page résumé destination | **View résumé** | Public and validated | One navigation action distinct from Connect | Keep | Targets the actual résumé below; no duplicate PDF behavior |
| Proof band | Give immediate scale, outcomes, or truthful differentiators | Optional authored Overview claims with member-supplied exact values | Optional validated public destination | Public only through normal owner preview and publish; no first-release metric source/provenance system | Fast quantitative/qualitative evidence | Keep optional | Zero to four items; one receives a feature treatment; AI cannot invent or alter a value |
| Proof item | Communicate one outcome or scope claim | Member supplies the exact value directly or explicitly in the current AI request; label is member-authored or accepted | One validated supporting destination or static presentation | Public authored projection; no source, evidence, verification badge, or provenance state in first release | One value and one concise label | Keep optional | Never force a metric; AI may preserve a supplied value and edit its label only |
| Career Arc / Career Focus | Show selected progression without repeating every role | One to four selected eligible résumé roles | View full experience or a specific role | Public projection over existing role records | Concise time/progression relationship | Keep optional | One role becomes Career Focus; dense role bodies stay below |
| Impact Highlights | Surface selected outcomes distinct from the proof band | Selected outcome/role/project records plus approved summary | Supporting experience, Work, Project, or public evidence | Public and source-linked | Explains why a result matters | Keep optional | Editor warns when it duplicates a proof item |
| Flexible Spotlight | Explain one capability, specialty, leadership theme, value, personal dimension, or future direction | Record-linked, authored, or hybrid content | Zero or one eligible destination | Public projection; personal material is optional and audience-controlled | Reusable bounded feature, not a hardcoded industry section | Keep optional | Replaces hardcoded Sustainment/Data/Systems sections |
| Spotlight media | Add context or atmosphere to a specific spotlight | Member-selected eligible media | Usually static; may share the block destination | Consent, audience, alt text, focal point, and withdrawal required | Supports one block's meaning | Keep optional | Missing media must produce a deliberate text-led variant |
| Skills preview | Show the member's selected strengths quickly | Selected eligible canonical skills | Specific `View all N skills` when more public skills exist | Public records only; link fails closed | Capability index into detailed résumé evidence | Keep optional | Renamed from Core Tools and placed before credentials |
| Education preview | Show selected formal learning without credential gatekeeping | Selected eligible education records | View Education only when an eligible destination has additional detail | Public records only | Education, not a proxy for value | Keep optional | One degree renders confidently; no forced filler |
| Certifications preview | Show selected eligible certifications | Selected certification records | View Certifications only when useful | Public records only; expiry/withdrawal handled | Certification-specific proof | Keep optional | Missing certification leaves no gap |
| Awards preview | Show selected recognition | Selected award records | View Awards only when useful | Public records only | Recognition-specific proof | Keep optional | Missing awards leaves no gap |
| Credentials grouping | Arrange Education, Certifications, and Awards efficiently | Presentation grouping only; category labels remain truthful | Child-specific destinations | Group omitted when no eligible child exists | Count-aware layout relationship | Keep as system layout | May pair sparse groups without inventing a combined credential |
| Quote / Principle | Add a short member-approved leadership or work principle | Member-authored/accepted text | Static or one precise Story destination | Public and optional | Voice/point of view | Keep optional | Must not repeat philosophy or hero copy |
| Philosophy / Future banner | State a bounded value or future-facing invitation | Member-authored/accepted projection | Optional Contact, Story, Goal/public future surface when eligible | Public and optional; no private goal leakage | Closing meaning before résumé | Keep optional | The member chooses philosophy or future direction when it adds value |
| Block action | Continue into the evidence or fuller public story | Validated eligible destination | One visible descriptive link; card surface may share exactly the same action | Removed if destination becomes unavailable | Makes the preview useful rather than decorative | Keep when meaningful | Generic `More` and dead links are prohibited |

### B3. Story & Career-specific relationships

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Story Spotlight | Give a concise human/professional origin or turning point | An explicitly eligible same-audience published Story projection plus an optional bounded teaser grounded in it | Read the eligible public Story | Never retrieves private Journal; omitted if no public Story projection exists | Connects career proof to selected published narrative | Keep optional | Standalone authored narrative uses Flexible Spotlight and cannot imply a Story destination |
| Story Chapters preview | Show two to five deliberately selected chapter cues | Eligible public Story chapter projections | Read the full public Story or a stable chapter destination | Public Story only; source/version pinned | Finite narrative map | Keep optional | One chapter folds into Story Spotlight rather than faking a list |
| Personal image | Show selected life context or identity | Member-selected eligible media | Usually static | Other-person consent, audience, alt text, and withdrawal required | Personal context distinct from professional evidence | Keep optional | Never required; avoid oversharing or implied documentary claims |
| Story image/banner | Establish narrative atmosphere | Member-selected eligible media | May share the Story destination | Same Story/media audience and consent rules | Narrative emphasis | Keep optional | Text-led Story must remain valid |

### B4. Work & Impact-specific relationships

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Executive Brief | Summarize professional value, operating context, and focus | Member-authored or accepted source-grounded projection | Optional full Experience destination | Public revision; not a duplicate résumé summary store | Work-first orientation | Keep optional / recommended in style | Valuable for a results-forward scan |
| Capability feature | Explain a selected area of practice | Hybrid projection over roles, outcomes, projects, and skills | Specific Experience, Work, Project, or Skills destination | Eligible public sources only | Explains how the member works, not just a label | Keep optional | Titles are member-defined; examples are not hardcoded |
| Outcomes tile group | Present two to eight related outcomes inside one feature | Eligible outcomes or confirmed facts | Individual supporting destinations when they differ | Public and source reviewed | Comparative evidence within one theme | Keep optional | Distinct from the zero-to-four top proof items |
| Professional evidence media | Provide approved context for a capability | Member-selected authentic media or clearly labeled illustration | Optional related destination | Consent, audience, provenance, alt text; generated imagery cannot pose as evidence | Context for one capability | Keep optional | No generic meeting image is required |
| Person behind the work | Add bounded personality/context to a results-forward profile | Member-authored projection plus eligible media | Optional Story/public personal destination | Optional and audience-controlled | Human counterpoint to work proof | Keep optional | It is a block choice, not a required hardcoded section |
| What I am building toward | State a deliberate public future direction | Member-authored projection; future goals remain private unless explicitly projected | Optional eligible future/Story/Contact destination | Never exposes private Goal Board content automatically | Forward-looking close | Keep optional | Useful when the member wants it; no gap when absent |

## C. Meaningful owner-editor item decisions

| Item | Member purpose | Source / capability truth | Action / destination | Privacy, audience, and lifecycle | Unique relationship on this page | Decision | Owner rationale |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Edit Overview entry | Enter authorized composition | Server-authorized owner capability, future | Opens private composer | Owner only | Single clear edit entry | Keep |
| Setup choice | Start from records, build manually, or ask AI for a proposal | All paths create the same private draft contract | Select a starting path | Owner only; no public effect | Reduces setup friction without making AI mandatory | Keep |
| Overview style selector | Compare Story & Career and Work & Impact | Two direction-approved style choices; exact manifests remain pending visual lock | Change draft style and preview | Owner only until publish | Presentation choice, not content duplication | Keep |
| Block catalog | Add one finite supported block | Approved block definitions only | Add to private draft | Owner only | Structured extensibility | Keep |
| Record selector | Choose eligible canonical/public records | Authorization-filtered records with source status | Add references to a block | Owner only; authorization before retrieval | Source grounding | Keep |
| Copy editor | Write or revise bounded projection text | Member-authored draft | Edit draft | Owner only until publication | Manual path | Keep |
| Ask AI action | Request a scoped proposal | Eligible selected sources only | Opens proposal comparison | Owner only; optional; never auto-applies | Assistance inside the current task | Keep optional |
| AI proposal comparison | Understand support and exact change | Proposed text/order plus cited sources | Accept into draft, edit, or reject | Private proposal lifecycle | Human decision point | Keep |
| Emphasis selector | Choose Feature, Standard, or Compact where supported | Manifest-approved variants | Change draft presentation | Owner only until publication | Bounded visual control | Keep |
| Reorder controls | Set semantic sequence | Current draft order | Drag plus move up/down/to-position | Owner only; keyboard equivalent required | Member-owned narrative order | Keep |
| Hide from Overview | Remove projection without deleting source | Draft visibility state | Hide/show block | Owner only; source remains canonical | Projection control | Keep |
| Destination selector | Choose one eligible continuation | Valid public destinations only | Set/change/remove destination | Owner only; revalidated at publication | Prevents dead or misleading actions | Keep |
| Media editor | Select, crop, focus, describe, and classify media | Eligible media records | Add/replace/remove; set focal point/alt/consent | Owner only until publication; audience and withdrawal governed | Safe media composition | Keep |
| Readiness status | Explain whether the draft can publish | Deterministic validators | Navigate to and fix issue | Owner only | Clear quality/trust feedback | Keep |
| Desktop/mobile/large-text visitor preview | See exact public result | Public representation of current draft | Change preview state; no public mutation | Owner only; must omit edit furniture/private data | Exact audience understanding | Keep |
| Save status / autosave | Confirm private work is preserved | Draft revision state | Retry on failure | Owner only | Draft durability | Keep |
| Publish Overview | Atomically replace public revision | Validated exact previewed revision | Explicit confirm and publish | Owner only; server-authorized; audited | Only public commit | Keep |
| Unpublish Overview | Remove the current public Overview and return to the existing Summary fallback | Current publication revision plus exact fallback public representation | Explicit confirm; concurrency-checked atomic withdrawal | Owner only; history retained; caches change only after success | Owner-controlled reversal of publication | Keep |
| Unpublish pending/success/failure | Tell the owner whether withdrawal took effect | Server transaction state | Retry on failure; return to exact public result | Owner only; failed operation leaves publication unchanged | Truthful withdrawal feedback | Keep |
| Restore prior publication | Recover an earlier accepted public result | Versioned prior publication | Preview then explicitly restore/publish | Owner only; creates a new revision | Reversibility | Keep |
| Corrective source supersession status | Explain that a prior public claim is no longer valid and has failed closed | Canonical lifecycle/validity state | Review corrected source and publish replacement | Owner only; public output omits invalid claim immediately | Prevent known stale professional claims | Keep |
| Arbitrary resize/coordinates/CSS | Create freeform layout | Unsupported | None | High breakage/accessibility risk | No necessary product job | Remove |

## D. Combined, removed, and deferred items

| Item | Decision | Replacement / destination / reason | Revisit trigger |
| --- | --- | --- | --- |
| Mockup Full Résumé summary | Remove | Real résumé begins immediately after the boundary | None unless page architecture changes |
| Separate Overview plus current Summary heroes | Combine | Published Overview absorbs Summary; Summary remains the no-publication/unpublish fallback | A future owner-approved page hierarchy change |
| Moving the current right ribbon to the left Context Rail | Defer | Separate résumé rail migration package under the approved standard | Exact package, visual authority, and owner acceptance |
| Concept top navigation/footer | Remove from Overview | Existing PeerSlate shell and current résumé ribbon; future Context Rail remains separately gated | A separately approved shell/navigation package |
| Hardcoded Systems Engineering, Sustainment, Data/AI, or similar sections | Combine into Flexible Spotlight / Capability feature | These are Pete fixture examples, not reusable product sections | A future broadly reusable block need |
| Repeated hero metrics and impact claims | Combine or select one use | Duplication warning requires one primary expression | Owner deliberately approves distinct meanings |
| Story Spotlight + Story Chapters + Philosophy all by default | Change to optional selections | Member includes only narrative blocks that add distinct value | Owner composition choice |
| Generic `More` | Remove | Destination-specific action with count/context | None |
| Visitor style toggle | Defer | One owner-selected published style | Explicit audience-projection package |
| Multiple public Overviews | Defer | One public publication at a stable location | Explicit audience/version product decision |
| Independently selectable Overview audience | Defer | First release inherits the public résumé audience and cannot be broader | Separate audience product decision |
| Arbitrary custom block type | Remove | Bounded Flexible Spotlight with finite fields | Proven reusable need plus new inventory/visual gate |
| AI-generated documentary-looking workplace/family media | Remove | Member-selected authentic media or clearly labeled illustration | Separate media-truth standard and owner approval |

## E. Lock check

- [x] Every meaningful item visible in the supplied concepts has a decision.
- [x] Owner editing controls and public states have distinct rows.
- [x] Repeated decoration may be handled by the visual system without separate
  rows only when it carries no claim, action, status, or destination.
- [x] Each retained public item has a distinct relationship; duplicate claims
  must combine or be removed.
- [x] Actions and destinations are defined truthfully, including unavailable
  states.
- [x] Privacy, canonical/projection, AI, draft/published, and Story/Journal
  boundaries are explicit.
- [x] Pete approved this exact inventory on 2026-07-26.
- [ ] ChatGPT has created the production-intent visual/state set.
- [ ] Pete has locked exact visual files and hashes.
- [ ] The locked visuals introduce no unlisted meaningful item.

Until the final four boxes are complete, this inventory permits requirements
discussion only. It does not authorize runtime implementation.

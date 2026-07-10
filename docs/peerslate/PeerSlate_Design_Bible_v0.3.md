# PeerSlate Design Bible

**Version:** 0.3  
**Status:** Approved Direction C foundation with multi-tenant, living-résumé, and voice-first product standards  
**Primary product statement:** Your Work. Your Story. Your Future.

## 1. Product Experience

PeerSlate is an evidence-backed professional story and growth platform. It should not feel like a conventional portfolio, résumé builder, social feed, dashboard, or generic AI wrapper. It should feel like a connected product experience in which a person can capture their work, explain their story, plan their future, practice how they communicate it, and connect with others making similar progress.

The governing metaphor is:

> Every page is a different room in the same premium building.

Each room may have its own atmosphere and dominant visual, but navigation, typography, surfaces, spacing, interaction patterns, evidence language, and product voice must make the whole platform unmistakably PeerSlate.

Beauty should come from scale, atmosphere, proportion, depth, typography, and restraint—not from adding more effects. Every scene should contain one dominant product object and enough visual calm for that object to feel important.

### 1.1 The three PeerSlate experiences

PeerSlate has three related but distinct experience modes.

#### Public Experience

The public entry experience sells the connected PeerSlate vision through cinematic product storytelling. It introduces Your Work, Your Story, Your Future, and connection through real, inspectable product demonstrations rather than generic feature claims. The current Experience page is expected to become the principal public landing experience.

#### Signed-in PeerSlate

The authenticated product is a working environment, not a marketing sequence. Its purpose is to help members capture progress, explore the Slate Feed, manage their Slate, use the Slate Board, pursue goals, connect with relevant people, and receive AI guidance. Cinematic qualities remain present through composition, atmosphere, and transitions, but productivity and clarity take priority.

#### Public and Recruiter Slate

A published Slate is a controlled, evidence-backed professional story. Visitors and recruiters can explore approved work, résumé content, skills, outcomes, and personal context; inspect supporting evidence; ask the profile AI questions; and use Interview Me where appropriate. Private drafts and unapproved sources must never appear in this mode.

These modes share one system but must not be visually or behaviorally identical. Marketing scenes may use guided scroll choreography. Signed-in pages must favor direct navigation, predictable controls, and persistent state. Public Slates must favor credibility, evidence inspection, and effortless scanning.

## 2. Experience Principles

1. **One unmistakable purpose per screen.** A visitor should understand the purpose of the current section within five seconds.
2. **The product is the star.** Interface examples, feature cards, evidence, and interactive demonstrations receive more visual weight than explanatory copy.
3. **Evidence over assertion.** Claims lead naturally to projects, outcomes, documents, metrics, or approved portfolio sources.
4. **Cinematic, not theatrical.** Motion creates continuity and focus. It must never delay understanding or compete with content.
5. **Editorial clarity with product precision.** Display typography carries emotion; interface typography carries function.
6. **Calm density.** Pages can contain meaningful depth without becoming visually crowded. Use progressive disclosure rather than shrinking everything.
7. **Connected experiences.** Ask AI, Interview Me, the interactive résumé, Skills and Evidence, Slate Feed, Slate Board, goals, progress, and people must feel like parts of one living system.
8. **Premium light-first usability.** Core application pages favor luminous, restrained light environments. Dark scenes are intentional moments, not the default solution for visual impact.
9. **Scale signals importance.** The dominant product demonstration should feel large, inspectable, and worthy of attention.
10. **Human before technological.** AI should help people explain, practice, connect, and grow. It should never make PeerSlate feel impersonal.
11. **Continuity without sameness.** Pages may change atmosphere, but they retain the same structural rhythm, materials, navigation, and interaction grammar.
12. **Trust is visible.** Privacy, evidence status, AI synthesis, and source grounding are communicated directly in the interface.
13. **Design for every Slate, not one example.** Pete's Slate is the demonstration model, but components, layouts, content rules, and AI behavior must support students, early-career members, career changers, freelancers, and senior professionals without Pete-specific hardcoding.
14. **Voice is a primary input.** Members may create, update, connect, and organize career information conversationally. Voice input must produce a reviewable structured proposal before anything is saved or published.
15. **Enter once, render everywhere.** The Résumé Ledger, Career Constellation, public Slate, AI grounding, skills, and evidence views must derive from the same approved structured data.

## 3. Current Live-Site Audit

### Preserve

- The Work → Story → Future → Connect narrative.
- The full-screen chapter transitions and environment changes.
- Newsreader for cinematic and editorial headlines.
- Inter for navigation, controls, labels, and body copy.
- The large glass cards that allow the environment to remain visible.
- The cyan-to-azure-to-indigo accent thread connecting otherwise different scenes.
- The sticky translucent navigation bar.
- Ask Pete AI and Interview Me as signature proof-driven experiences.
- The compact Skills and Evidence cards with reveal or flip behavior.
- The use of real outcomes such as $36M contract oversight, 70% repair/test improvement, 52% missing-part reduction, and $9.1M control-account execution.
- Slate Feed distinctions among People & Progress, Pulse, and Break.
- The connection between goals, progress updates, relevant people, and AI-recommended next actions.

### Improve next

- Standardize glass opacity, blur, border, radius, and shadow across sections.
- Reduce the visual mismatch between cinematic marketing scenes and utility/application pages.
- Give Future and Connect the same product-specific depth already present in the Work chapter.
- Make the signed-in Overview clearly centered on the Slate Feed and Ask AI.
- Replace generic feature labels with recognizable PeerSlate UI demonstrations wherever possible.
- Tighten hierarchy in sections containing four equal cards so there is still one dominant focal point.
- Protect text contrast when imagery becomes bright, detailed, or high-saturation.
- Establish a consistent transition language between backgrounds instead of relying only on hard scene changes.
- Define responsive rules before adding more animation or content.
- Resolve the signed-in information architecture so pages, tabs, and deep links do not compete.

## 4. Brand Personality

PeerSlate should feel:

- Intelligent, human, reflective, ambitious, credible, optimistic, and quietly advanced.
- More like an editorial product story than a technology landing-page template.
- More personal than LinkedIn, more alive than a résumé, and more structured than a general social network.
- Premium without feeling exclusive, sterile, or overly corporate.
- Aspirational while remaining grounded in real work, evidence, and progress.

Avoid:

- Neon-heavy AI-product clichés.
- Excessive glowing borders.
- Tiny dashboard cards used to fit too much above the fold.
- Stock corporate illustrations that are not connected to the product.
- Decorative scenery that overpowers the interface.
- Motion on every element.
- Multiple equally loud calls to action.
- Glass surfaces without sufficient contrast or purpose.
- Generic promises such as “unlock your potential” when a specific PeerSlate benefit can be shown.

## 5. Typography

### Families

| Role | Family | Use |
| --- | --- | --- |
| Cinematic display | Newsreader, Georgia, serif | Hero statements, chapter titles, emotional section headlines |
| Product UI | Inter, ui-sans-serif, system-ui, sans-serif | Navigation, controls, body copy, cards, metadata, forms, and long-form product content |

Version 0.3 locks two primary families: Newsreader and Inter. A third editorial family should be introduced only if real reading tests prove that Inter cannot serve longer personal-story passages.

### Type scale

| Token | Desktop | Mobile | Use |
| --- | ---: | ---: | --- |
| `display-hero` | clamp(4rem, 6.4vw, 5.75rem) | clamp(2.8rem, 12vw, 4rem) | Opening statement only |
| `display-section` | clamp(3rem, 5vw, 4.5rem) | clamp(2.25rem, 9vw, 3.25rem) | Chapter and major section titles |
| `title-card` | clamp(1.5rem, 2vw, 2.25rem) | 1.5–1.875rem | Feature and product-card titles |
| `heading-ui` | 1.25–1.5rem | 1.125–1.375rem | Panels and application modules |
| `body-lg` | 1.125–1.25rem | 1.05–1.125rem | Lead copy |
| `body` | 1rem | 1rem | Default copy |
| `label` | 0.75rem | 0.75rem | Eyebrows and metadata; uppercase sparingly |

### Rules

- Display headlines may use tight tracking from `-0.015em` to `-0.02em`.
- Body text should maintain a line height of approximately `1.55–1.65`.
- Keep centered lead paragraphs to roughly 55–65 characters per line.
- Do not use the serif face for buttons, navigation, form fields, data, or dense application UI.
- Use sentence case for controls and title case only when the editorial tone warrants it.
- Product-stage copy should be concise enough that the demonstration remains dominant.
- Never reduce interface text below readable product sizes merely to preserve a desktop composition.

## 6. Color System

The current site contains several legacy color families. Version 0.3 locks the cool-luminous Direction C palette as the default PeerSlate system.

| Token | Value | Purpose |
| --- | --- | --- |
| `ink-950` | `#0A1B36` | Primary text on light scenes |
| `night-950` | `#060B18` | Deep page background and dark transitions |
| `surface-light` | `#F6F8FC` | Clean application surface |
| `surface-warm` | `#FFF8EF` | Warm story and evidence scenes |
| `text-on-dark` | `#F2F7FF` | Primary text on dark imagery |
| `text-muted-dark` | `#8996A8` | Supporting text on dark surfaces |
| `product-indigo` | `#4F5BD5` target | Primary product actions; final production shade must maintain at least 5:1 contrast with white text |
| `connection-azure` | `#4EA3FF` | Connection and active product states |
| `ai-cyan` | `#2EC8D3` | AI, analysis, listening, and active intelligence |
| `evidence-amber` | `#D7A33E` | Achievement, evidence, verification, and selective emphasis |
| `transition-violet` | Provisional supporting shade | Rare atmospheric transitions only; not a default semantic action color |
| `success` | `#24A36A` | Verified and completed states |
| `warning` | `#D48727` | Attention states |
| `danger` | `#C9405B` | Destructive and error states |

### Accent rules

- The cyan-to-azure-to-indigo thread is the approved PeerSlate signature gradient.
- Indigo communicates product identity, trust, and primary action.
- Azure communicates connection, movement, and active product states.
- Cyan is reserved for AI, voice listening, analysis, and active intelligence.
- Amber is reserved for achievement, verification, evidence, and rare premium emphasis.
- Pink, rose, magenta, and coral are not semantic interface colors. Warmth may appear naturally in approved environmental imagery without becoming a button, navigation, progress, or card-border color.
- Violet may bridge selected atmospheric transitions but must not become a competing interface identity.
- Use one dominant accent within a viewport. Supporting accents remain subordinate.
- Application surfaces should remain predominantly neutral, ink, and blue; signature colors should guide attention rather than tint everything.
- Never rely on color alone to communicate a state.

## 7. Spacing and Layout

### Base system

Use a 4px base with the following preferred steps:

`4, 8, 12, 16, 24, 32, 48, 64, 80, 96, 128, 160`

### Containers

| Token | Recommendation |
| --- | --- |
| `content-max` | 1360px |
| `reading-max` | 720px |
| `wide-card-max` | 1360px |
| `cinematic-stage-max` | 1520–1600px |
| Desktop gutters | 48–64px |
| Tablet gutters | 32px |
| Mobile gutters | 20px |

### Section composition

- Cinematic chapters use `min-height: 100svh`, not fixed `100vh`.
- A cinematic product demonstration generally occupies 76–92% of the usable viewport width on desktop, up to `cinematic-stage-max`.
- The primary product stage generally occupies 52–68svh in height when the content supports that scale.
- The section headline and concise supporting copy normally sit above the product stage. Together they should not consume more than approximately the upper 20–25% of a cinematic scene.
- Product UI must remain readable without zooming. Do not shrink a complete desktop screen into a decorative thumbnail.
- Supporting cards should feel compositionally attached to the dominant product stage rather than scattered around it.
- In four-card arrangements, one card, interaction, or staged sequence must establish priority. Four equal cards are not automatically four equal focal points.
- Use generous vertical transitions: 96–160px on desktop and 64–96px on mobile.
- Application pages use the same container widths and spacing rhythm even when they are not full-screen scenes.
- Do not surround a small product mockup with excessive decorative empty space. Whitespace should create importance, not distance.

### Composition recipes

The system should support a small set of repeatable recipes:

1. **Editorial lead + product stage:** centered headline, short explanation, nearly full-width product demonstration.
2. **Product stage + evidence rail:** dominant interface with compact, inspectable evidence at one side or below.
3. **Guided sequence:** one primary card changes state while surrounding copy remains stable.
4. **Museum object:** résumé, timeline, or artifact receives quiet space with evidence positioned like gallery context.
5. **Working canvas:** an expansive Slate Board or planning surface with controls kept at the edges.
6. **Feed focus:** central feed column or gallery with AI and progress context orbiting it without becoming equal columns.

## 8. Glass and Surface System

Glass is a hierarchy, not one universal effect.

### `glass-hero`

- Background: white at 10–16% over dark imagery, or white at 34–48% over light imagery.
- Backdrop blur: 20–28px.
- Border: 1px solid white at 24–36%.
- Radius: 28–32px.
- Shadow: `0 24px 70px rgba(7,16,36,.16)`.
- Use for one primary experience panel per viewport.

### `glass-card`

- Background: white at 12–22% over dark imagery, or white at 42–58% over light imagery.
- Backdrop blur: 14–20px.
- Border: 1px solid white at 20–32%.
- Radius: 22–26px.
- Shadow: `0 18px 45px rgba(0,0,0,.14)`.
- Use for product cards and feature demonstrations.

### `glass-control`

- Background: white at 66–82%.
- Backdrop blur: 10–14px.
- Radius: 999px for pills, 12–16px otherwise.
- Use for navigation, compact controls, filters, and tags.

### `solid-surface`

- Use for forms, long reading, dense data, accessibility fallbacks, and any content for which glass reduces clarity.
- Solid surfaces remain part of the design language through the same radii, typography, spacing, and shadow hierarchy.

### Rules

- Every glass surface must pass contrast requirements against the brightest and darkest regions of its background.
- If readability depends on a specific part of an image staying dark, add a local scrim inside the section.
- Avoid nested glass on glass unless the inner surface is a functional control or evidence item.
- Do not add glow to every border. Reserve glow for active AI or signature moments.
- Glass must never be required for identity. The design should remain recognizably PeerSlate when accessibility or device support requires a solid fallback.

## 9. Environmental and Image Art Direction

Backgrounds create atmosphere, but the product remains the subject.

### Environmental principles

- Each room receives one emotional atmosphere, one dominant color family, and one primary depth treatment.
- Prefer luminous, aspirational environments with believable light, depth, and negative space.
- Avoid random scenery that has no emotional relationship to the page’s purpose.
- Background detail should be lower behind text and interface surfaces and may become richer toward the edges.
- Establish foreground, midground, and background layers when depth materially improves the composition.
- The visual horizon, major subject, or brightest highlight should not intersect important text or controls.
- Environmental changes should feel like moving through one connected world, not switching between unrelated wallpapers.

### Safe-zone requirements

Every approved background asset must document:

- Desktop, ultrawide, tablet, and mobile crops.
- Primary interface safe zone.
- Headline safe zone.
- Brightest and darkest regions.
- Required scrim or overlay.
- Focal point and acceptable crop range.
- Whether the asset can support light text, dark text, or both.

### Asset rules

- Use art-directed `<picture>` sources rather than relying on one crop for every device.
- Prefer AVIF with WebP fallback where browser support and image quality permit.
- Do not embed essential text in background images.
- Avoid fixed-background behavior on mobile when it causes rendering or scroll problems.
- Use video only when movement contributes meaningfully to the story and a high-quality static fallback exists.
- Generated imagery must be reviewed for visual defects, accidental symbolism, inconsistent lighting, and implausible details before use.

### Scene transitions

- Bridge rooms through shared light direction, color migration, atmospheric haze, or a continuous accent thread.
- Crossfades should not expose low-contrast intermediate states.
- A transition may briefly become abstract, but the next room’s dominant object should become understandable quickly.
- Never use a dramatic transition solely to disguise slow asset loading.

## 10. Room Identity Matrix

The matrix translates “different rooms, same building” into page-level direction. Atmospheres remain subject to visual testing, but each room must retain a distinct emotional purpose and dominant product object.

| Room | Emotional purpose | Dominant product object | Provisional atmosphere | Motion signature |
| --- | --- | --- | --- | --- |
| Public Experience | Wonder and discovery | Large product demonstrations | Evolving cinematic journey connected by the cyan-to-indigo thread | Calm chapter transitions |
| Overview | Clarity and momentum | Slate Feed + Ask AI | Luminous azure morning and restrained depth | Feed surfacing and quiet AI readiness |
| My Story | Reflection and humanity | Journey, turning points, and growth | Warm editorial light with personal depth | Progressive reveals |
| Résumé | Credibility and inspection | Living Résumé Ledger followed by Career Constellation | Quiet museum that evolves into a luminous career path | Chapter selection, evidence flips, and constellation materialization |
| Slate Feed | Discovery and progress | People & Progress, Pulse, and Break | Airy living knowledge gallery | Cards surface by relevance, not spectacle |
| Slate Board | Possibility and connection | Visual planning and goal canvas | Expansive translucent workspace | Lines and relationships resolve into view |
| My Slate | Ownership and coherence | Story, paths, evidence, and progress | Personal studio with organized layers | Sections assemble into a whole |
| Goals and Future | Direction and optimism | Roadmap, milestones, and matched people | Bright horizon with forward depth | Progress advances along a visible path |
| Ask AI | Intelligence and trust | Answer with inspectable evidence | Focused frosted environment | Evidence resolves alongside synthesis |
| Interview Me | Practice and confidence | Question, score, coaching, and ideal answer | Premium coaching studio | Guided state progression |

No page should invent a new material system, navigation model, or unrelated visual personality merely to feel different.

## 11. Core Components and Signature Feature Anatomy

### Global foundations

1. `GlobalNavigation`
2. `AuthenticatedShell`
3. `PublicSlateShell`
4. `CinematicChapter`
5. `SectionIntro`
6. `GlassHeroPanel`
7. `FeatureShowcaseCard`
8. `ProductDemoFrame`
9. `PrimaryButton` and `SecondaryButton`
10. `EvidenceChip`
11. `PrivacyBadge`
12. `VerificationBadge`
13. `ChapterTransition`
14. `GlobalFooter`

### Slate Feed system

15. `SlateFeed`
16. `SlateFeedTabs`
17. `ProgressComposer`
18. `ProgressCard`
19. `PeopleProgressCard`
20. `PulseCard`
21. `BreakCard`
22. `FeedFilter`
23. `SuggestedConnectionCard`
24. `AINextActionCard`

The Slate Feed is not one generic card list. Its three modes have distinct purposes:

- **People & Progress:** ongoing work, goals, shared interests, relevant people, discussion, and encouragement.
- **Pulse:** meaningful wins, milestones, completions, and community momentum.
- **Break:** a deliberate pause containing concise reflection, encouragement, or perspective.

### Slate and evidence system

25. `InteractiveResumeFrame`
26. `ResumeLedger`
27. `ResumeTimelineRail`
28. `ResumeChapterPanel`
29. `CareerConstellation`
30. `TimelineEventNode`
31. `ResumeEvidenceRail`
32. `SkillEvidenceCard`
33. `SkillEvidenceFlip`
34. `EvidenceDrawer`
35. `MilestoneCard`
36. `MySlatePath`
37. `DailySlate`

#### Living Résumé system standard

- The Résumé Ledger and Career Constellation are two synchronized views of the same approved structured career data.
- The Ledger appears first and provides the detailed, recruiter-friendly résumé. Its integrated timeline is the résumé navigation and structural spine, not a separate set of cards.
- The Career Constellation materializes below the Ledger as a cinematic summary of the member's defining education, experience, credential, and future chapters.
- Selecting a timeline chapter updates content inside the résumé rather than opening an unrelated résumé surface.
- Education, work experience, credentials, projects, and future development may all appear as timeline events.
- The Ledger may show the complete timeline. The Constellation normally shows four to six defining chapters and provides access to grouped or additional history.
- Layouts must support zero-work-history students, early-career members, career changers, freelancers, mid-career members, and senior professionals with extensive histories.
- Every accomplishment, skill, metric, and evidence item retains its source relationship to a profile, role, project, education item, or credential. Career-wide highlights must never appear as though they belong to the selected role.
- Skill chips remain compact. Their front shows the skill and evidence count; their back reveals the two or three strongest approved proof points plus the originating role or project.
- Members enter information once. Both résumé views, Ask AI grounding, public profile content, and evidence displays render from that same approved data.
- Full interaction, content-selection, data, voice, and variable-layout requirements are governed by `PS-FEAT-001_Living_Resume_Voice_Blueprint.md`.

### Slate Board, goals, and people

38. `SlateBoardCanvas`
39. `BoardWidget`
40. `GoalProgressCard`
41. `GoalConnection`
42. `MatchedPeople`
43. `PeopleConnectionCard`
44. `MentorshipCard`

The Slate Board must look and behave like a real visual thinking workspace—not a generic feature card. Marketing demonstrations should show an authentic portion of the board, including goals, relationships, notes, paths, or collaborative connections.

### AI and interview system

45. `ProfileAIExperience`
46. `EvidenceAnswer`
47. `SourceInspector`
48. `InterviewExperience`
49. `InterviewQuestion`
50. `AnswerRecorder`
51. `InterviewScore`
52. `CoachingFeedback`
53. `IdealAnswer`
54. `WhyThisAnswerWorks`

### Voice and conversational editing system

55. `VoiceCaptureControl`
56. `ListeningIndicator`
57. `LiveTranscript`
58. `ClarificationPrompt`
59. `StructuredChangePreview`
60. `SourceAssignmentControl`
61. `VisibilityConfirmation`
62. `VoiceDraftHistory`

`ProfileAIExperience` is the reusable platform component. “Ask Pete AI” is Pete’s instance; other public Slates use “Ask [Name] AI.”

Every Storybook entry must document variants, content limits, loading and error states, empty states, offline behavior where relevant, public and private states, light and dark use, mobile behavior, keyboard behavior, 200% zoom behavior, and reduced-motion behavior.

## 12. Overview Composition Standard

The Overview is PeerSlate’s living command center. The Slate Feed is the visual centerpiece, while Ask AI remains immediately visible and actionable. Pulse, goals, progress, relevant people, résumé activity, and recommended next actions orbit these two primary experiences without competing with them.

### Hierarchy

1. **Slate Feed:** the largest and most active surface.
2. **Ask AI:** persistent or immediately accessible, visually significant, and grounded in the member’s own Slate.
3. **Next best action:** one clear recommendation based on recent progress, goals, or incomplete Slate work.
4. **Supporting context:** goals, Pulse, people, evidence activity, and progress summaries.

### Rules

- The Feed must not be reduced to a small dashboard widget.
- Ask AI must not be hidden in an undifferentiated utility menu.
- Supporting modules may rearrange responsively, but Feed and AI priority must survive every breakpoint.
- Avoid a grid of equally weighted analytics cards above the Feed.
- The opening viewport should communicate that PeerSlate is alive: people are progressing, goals are moving, evidence is growing, and AI can help determine what comes next.
- Personal metrics should support decisions, not exist merely to decorate the dashboard.

## 13. Motion Language

Motion should explain hierarchy, continuity, or change.

| Motion | Duration | Easing | Use |
| --- | ---: | --- | --- |
| Micro interaction | 120–180ms | ease-out | Hover, press, focus, small state changes |
| Component entrance | 280–450ms | cubic-bezier(.22,.8,.25,1) | Cards and panels entering view |
| Chapter transition | 650–1000ms | cubic-bezier(.22,.8,.25,1) | Background and full-section transitions |
| Stagger | 60–100ms | — | Small groups only |

### Motion rules

- Animate opacity and transforms before layout properties.
- Default entrance travel stays within 16–32px.
- Parallax is subtle and never impairs reading.
- Only one major animation commands attention at a time.
- Scroll-driven sequences remain understandable when the user scrolls quickly.
- Respect `prefers-reduced-motion`; remove parallax, pinning, auto-flips, and long transitions while preserving all content.
- Do not autoplay repeating decorative animation near forms or reading areas.
- A product demonstration may progress through states, but the user must be able to pause, reverse, or inspect important information.
- Card flips require an accessible non-flip alternative and must not hide essential information.

### Choreography pattern

Cinematic scenes should generally follow:

1. Establish the room and headline.
2. Introduce the dominant product object.
3. Demonstrate one meaningful state change.
4. Hold long enough for inspection.
5. Transition without destroying reading continuity.

Signed-in application pages should not reproduce this sequence for ordinary navigation or repeated tasks.

## 14. Responsive Behavior

### Desktop, 1200px+

- Use full cinematic composition and four-card rows where content remains readable.
- Keep product examples large enough to inspect.
- Allow the cinematic stage to approach the viewport edges while respecting safe gutters.
- Limit navigation choices and preserve strong center alignment in editorial scenes.

### Tablet, 768–1199px

- Move four-card rows to a 2×2 grid.
- Shorten pinned scroll sequences.
- Convert side-by-side product explanations into stacked layouts when either side falls below 360px.
- Preserve the dominant object; do not create four equally loud stacked sections.

### Mobile, below 768px

- Use one card per row or a clearly signposted horizontal carousel when comparison matters.
- Keep narrative order in normal document flow.
- Avoid sticky scenes that trap scrolling.
- Maintain at least 44×44px interactive targets.
- Do not shrink desktop mockups until their UI becomes unreadable. Crop to the most important feature or use progressive disclosure.
- Use mobile-specific background crops and simplify decorative depth where necessary.
- Keep Feed and Ask AI priority intact on the signed-in Overview.

### Responsive testing matrix

At minimum, review at:

- 2560×1440
- 1920×1080
- 1440×900
- 1024×1366
- 768×1024
- 430×932
- 390×844
- 360×800
- 200% browser zoom
- Reduced-motion and increased-contrast preferences

## 15. Accessibility Standards

- Target WCAG 2.2 AA.
- Maintain at least 4.5:1 contrast for normal text and 3:1 for large text and meaningful interface graphics.
- Provide visible keyboard focus for every control.
- Preserve logical heading order regardless of visual scale.
- All interactive cards need a clear accessible name and state.
- Provide text alternatives for meaningful screenshots and imagery.
- Do not put essential information only inside animation, hover, card flips, or canvas content.
- Announce dynamic AI results appropriately without moving keyboard focus unexpectedly.
- AI answers must visibly distinguish generated synthesis from cited portfolio evidence.
- Slate Board content requires an accessible list or structured alternative to its spatial canvas.
- Carousels and staged product demonstrations require keyboard controls, status, and pause behavior.
- Contrast testing must include the brightest and darkest approved crop of every environmental background.
- Support zoom and text reflow without obscuring controls or forcing two-dimensional page scrolling for ordinary content.

## 16. Audience, Privacy, and Evidence States

PeerSlate must make audience and source boundaries visible without making every surface feel administrative.

### Audience modes

| Mode | May see | Must not see |
| --- | --- | --- |
| Owner | Private drafts, public content, edit controls, AI coaching, visibility settings | Sources unavailable to the owner |
| Public visitor | Published story, approved evidence, public goals and profile content | Private drafts, private goals, internal AI notes |
| Recruiter | Approved professional content, résumé, evidence, fit exploration, public AI answers | Unapproved sources or private personal content |
| Collaborator or connection | Explicitly shared goals, boards, progress, and discussions | Unshared Slate or board content |

### Content-state vocabulary

- **Private:** visible only to the owner or explicitly authorized collaborators.
- **Draft:** not yet published or approved for public AI grounding.
- **Published:** intentionally visible to the selected audience.
- **Evidence-backed:** supported by inspectable approved evidence.
- **Verified:** confirmed through the defined PeerSlate verification process; this term must not be used casually.
- **AI synthesis:** generated from allowed sources and clearly labeled as synthesis.
- **Insufficient evidence:** the system cannot responsibly make the requested claim.

### Rules

- Visibility changes require clear previews of who can see the result.
- Public AI answers use only sources approved for that public audience.
- Evidence chips reveal enough source context to establish trust without exposing restricted content.
- Generated, user-authored, and evidence-verified content must be visually distinguishable.
- Privacy controls remain understandable in plain language and never rely only on icons.

## 17. AI Interaction Standards

Ask AI and Interview Me are flagship PeerSlate experiences, not ordinary chat windows.

### Shared standards

- Always state the grounding source: approved portfolio evidence, résumé evidence, or user-provided interview material.
- Show evidence links or chips near the answer.
- Allow the user to inspect why an answer or score was produced.
- Separate coaching feedback from factual claims.
- Scores include specific, actionable reasoning and do not imply certainty beyond the rubric.
- Provide clear loading, unavailable, insufficient-evidence, permission, and retry states.
- Never hide the close control or trap the user in an overlay.
- On scroll-driven marketing sections, open demos close or safely collapse when their section leaves the viewport.
- Ask AI should appear closer to the control or content that opened it rather than feeling detached from the page.

### Ask AI answer anatomy

1. Direct answer.
2. Evidence-backed summary.
3. Supporting evidence chips or citations.
4. Optional “why this answer” or source inspection.
5. Suggested related questions or next action.

Ask AI must say when approved evidence is absent or conflicting. It must not fill gaps with plausible but unsupported career claims.

### Interview Me learning loop

Interview Me should support the complete progression:

1. Present a relevant interview question.
2. Accept a typed or recorded answer.
3. Score against a visible, appropriate rubric.
4. Explain what was strong.
5. Identify specific improvements.
6. Provide an ideal evidence-grounded answer.
7. Explain why the ideal answer works.
8. Allow another attempt and show meaningful improvement.

The ideal answer must remain faithful to the member’s actual evidence. Coaching should help the user communicate truth more effectively, not manufacture experience.

## 18. Voice-First and Conversational Editing Standards

Voice is a primary creation and maintenance channel across the signed-in product. It is not limited to interview recording or search.

### Supported voice intentions

- Add or revise a role, education item, credential, project, accomplishment, skill, goal, or evidence note.
- Assign an accomplishment or evidence item to the correct role or project.
- Request an AI rewrite, stronger résumé bullet, summary, or evidence connection.
- Change visibility to draft, private, published, or another approved audience.
- Navigate the Slate, inspect evidence, and ask what information is incomplete.
- Correct dates, titles, organizations, ordering, and timeline relationships.

### Required conversational workflow

1. Capture speech and display an editable transcript.
2. Interpret the request into a structured proposed change.
3. Identify the affected profile, timeline chapter, skill, evidence item, and visibility state.
4. Ask a focused clarification when the source, role, date, claim, or visibility is ambiguous.
5. Show a before-and-after preview or structured change summary.
6. Require explicit member approval before committing the change.
7. Never publish or expand AI grounding automatically merely because a voice draft was saved.
8. Preserve source provenance and the original member wording when AI proposes a rewrite.

### Voice interaction rules

- Voice must have a complete keyboard and text alternative; no essential action is voice-only.
- Listening, transcribing, processing, clarification, preview, committed, cancelled, unavailable, and error states must be visibly distinct.
- Audio capture must have an obvious stop control and may not continue across pages without a persistent visible indicator.
- Raw audio retention requires an explicit product policy and member disclosure. The preferred default is to retain the approved transcript and structured change, not raw audio, unless the member intentionally saves a recording.
- Voice drafts are private until approved.
- Visitor-facing Ask AI and owner-facing editing AI are separate permission contexts.
- AI may recommend structure and wording, but the member remains the authority on truth, source assignment, privacy, and publication.
- The system must support commands such as: “Add this to my L3Harris chapter, connect it to MBSE, and keep it private for now.”

## 19. Product Voice and Writing Standards

PeerSlate speaks with confidence, warmth, specificity, and restraint.

### Voice principles

- Lead with the outcome, then explain the capability.
- Prefer specific PeerSlate language over generic technology claims.
- Use plain language even when the underlying system is technically sophisticated.
- Headlines may be emotional; controls, permissions, errors, and navigation must be literal.
- Explain why an action matters when the consequence is not obvious.
- Use evidence language consistently: source, evidence, approved, published, verified, and AI synthesis are not interchangeable.

### Preferred patterns

- “Explore the evidence” instead of “Learn more” when evidence is the destination.
- “Ask Pete AI” for Pete’s public Slate and “Ask [Name] AI” as the reusable product pattern.
- “Why this answer works” for interview explanation.
- “Who can see this?” for visibility explanation.
- “What should I do next?” for contextual coaching.

### Avoid

- Empty promises such as “revolutionize your career.”
- AI hype that does not describe a real capability.
- Recruiter jargon when ordinary professional language is clearer.
- Long paragraphs above product demonstrations.
- Different names for the same feature across navigation, headings, and controls.

## 20. Information Architecture

The final authenticated architecture remains a version 1.0 decision, but the design system must use one canonical hierarchy once it is approved.

### Provisional Slate hierarchy

- **The Slate**
  - **Slate Feed**
    - People & Progress
    - Pulse
    - Break
  - **Slate Board**
  - **My Slate**
    - Slate Paths incorporated into My Slate
  - **Daily Slate**

Goals, shared progress, people matching, and AI coaching should connect across these areas rather than becoming isolated products. A tab may have its own deep link, but that does not automatically make it a separate top-level destination.

### Architecture rules

- Global navigation expresses product domains, not every available view.
- Tabs switch closely related views within a domain.
- Deep links preserve shareability and return state without inflating navigation.
- The same feature name is used in navigation, page titles, analytics, Storybook, and code documentation.
- Public and signed-in navigation may differ, but their relationship must remain understandable.
- Before implementation, produce an approved route map showing owner, public, recruiter, and unauthenticated access.

## 21. Page Roles

| Page or area | Single dominant purpose |
| --- | --- |
| Public Experience | Sell the connected PeerSlate product through cinematic, inspectable storytelling |
| Overview | Center the signed-in experience on the Slate Feed, Ask AI, and one clear next action |
| Public Slate | Present a controlled, evidence-backed professional story to visitors and recruiters |
| My Story | Reveal the person, journey, values, turning points, and growth behind the work |
| Résumé | Present a generated Living Résumé Ledger followed by a Career Constellation, both linked to inspectable evidence and the member's approved timeline |
| Slate Feed | Deliver progress, people, wins, and reflection through People & Progress, Pulse, and Break |
| Slate Board | Provide a collaborative visual thinking, planning, and goal-mapping workspace |
| My Slate | Unite the member’s story, paths, evidence, goals, and progress into one owned space |
| Goals and Future | Turn aspirations into a visible roadmap connected to milestones, evidence, and relevant people |
| Ask AI | Let visitors or members question approved work and receive grounded, inspectable answers |
| Interview Me | Turn evidence into practice, coaching, scoring, ideal answers, and stronger retakes |

## 22. Performance and Visual-Quality Budgets

Cinematic quality must not make PeerSlate slow, unstable, or inaccessible.

### Web-vitals targets

- Largest Contentful Paint: under 2.5 seconds at the 75th percentile.
- Interaction to Next Paint: under 200ms at the 75th percentile.
- Cumulative Layout Shift: below 0.1.
- Page content and navigation remain usable before nonessential cinematic assets finish loading.

### Asset and runtime rules

- Preload only the immediate hero asset required for first meaningful display.
- Lazy-load later chapter backgrounds and below-the-fold product media.
- Supply responsive image sizes instead of sending a 4K asset to every device.
- Provide lightweight poster and reduced-data alternatives for video.
- Keep scroll-linked animation work off the main thread where practical.
- Prefer transforms and opacity for motion; avoid repeated layout-triggering animation.
- Avoid loading the full authenticated application merely to render a marketing demonstration.
- Use representative static or lightweight interactive product demos when a live embedded application would harm performance or reliability.

### Visual QA requirements

- Compare approved designs and implementation at every viewport in the responsive matrix.
- Test environmental crops with real content, long names, missing images, and maximum-length supported text.
- Review glass and text against both high- and low-brightness regions.
- Check hover, focus, active, loading, empty, error, permission-denied, insufficient-evidence, offline, and reduced-motion states.
- Confirm that the dominant product object remains dominant after responsive rearrangement.

## 23. First Implementation Sequence

### Foundation sprint

1. Consolidate colors into semantic tokens and mark provisional brand decisions clearly.
2. Implement the type scale and spacing scale.
3. Implement the glass hierarchy plus solid-surface fallback.
4. Build buttons, chips, navigation, privacy and verification states, and focus treatments.
5. Build `CinematicChapter`, `SectionIntro`, `ProductDemoFrame`, and `FeatureShowcaseCard` in Storybook.
6. Build the first Slate Feed card family and Ask AI evidence-answer anatomy.
7. Add responsive, reduced-motion, loading, empty, error, permission, and long-content stories.
8. Replace one current Experience-page chapter with the new components as a pilot without changing live functionality elsewhere.

### Recommended pilot

Use **Your Work** as the visual-system pilot because it already contains the richest product-specific content: flagship work, Ask Pete AI, Interview Me, Skills and Evidence, and the career timeline. It will test typography, backgrounds, glass, large product stages, interaction, evidence, motion, privacy language, and responsiveness before the system is applied elsewhere.

Use the **Overview Feed + Ask AI composition** as the first authenticated-product pilot. It will test whether the cinematic language can become a practical, living application without collapsing into a conventional dashboard.

## 24. Decisions Still to Lock

- Final room atmospheres and approved environmental background set.
- Whether cinematic backgrounds use fixed images, art-directed responsive images, restrained video, or layered CSS and image compositions.
- The signed-in navigation architecture after the proposed Slate, My Slate, Slate Paths, and People & Progress consolidation.
- The role and long-term placement of Daily Slate.
- The final component framework and current repository structure.
- The evidence-verification definition and which states may use the word “verified.”
- The exact recruiter-view permissions and whether Interview Me is public, owner-only, or configurable.
- Final speech provider, language coverage, audio-retention policy, and cost limits for voice capture.
- Final AI-ranking rubric for featured résumé bullets and defining Career Constellation chapters.

Unresolved decisions must be labeled provisional in Figma, Storybook, documentation, and code. They should not silently become permanent through implementation convenience.

## 25. Definition of Done for Version 1.0

The Design Bible reaches version 1.0 when:

- Every semantic design token exists in code and Storybook.
- Core components have approved desktop, tablet, mobile, light, dark, solid-surface, and reduced-motion variants.
- The public Experience, signed-in Overview, and public Slate all use the system successfully.
- The Overview clearly preserves Slate Feed and Ask AI dominance at every breakpoint.
- Every room has an approved identity, background family, dominant product object, and transition behavior.
- Signature experiences have documented anatomy, states, permissions, and responsive behavior.
- The route map and information architecture are approved.
- Accessibility and performance budgets are tested rather than merely documented.
- Owner, public visitor, recruiter, collaborator, private, draft, published, evidence-backed, verified, and AI-synthesis states are consistently represented.
- Visual QA passes the required viewport, zoom, contrast, reduced-motion, long-content, and failure-state matrix.
- Designers and developers can build a new PeerSlate page without inventing new spacing, glass, typography, button, evidence, privacy, motion, or background rules.
- A person unfamiliar with the implementation can explain what makes PeerSlate visually and functionally distinct after reading this document.
- The Résumé Ledger and Career Constellation render from the same multi-tenant structured data and pass student, early-career, career-changer, mid-career, freelancer, and senior-career content tests.
- Voice-created changes always produce an editable transcript, structured preview, source assignment, visibility state, and explicit approval step before commit or publication.
- No component, prompt, example, data query, or layout depends on Pete-specific values to function.

---

**Immediate next action:** complete Foundation C tokens and preview, then use `PS-FEAT-001_Living_Resume_Voice_Blueprint.md` to design and prototype the generated Résumé Ledger, Career Constellation, compact Skill Evidence Flip, and voice change-preview workflow without applying them to existing pages prematurely.

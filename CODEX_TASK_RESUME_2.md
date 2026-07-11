# PeerSlate Resume 2 — Codex Implementation Brief

## Objective

Create a **separate alternate résumé experience named “Resume 2”** based on the supplied full-page mockup.

The existing résumé page is **Resume 1** and must remain available for direct side-by-side comparison. Do not replace it.

Use the supplied blue-sky and enlarged-mountain artwork as the background for Resume 2. It contains **no people**.

The current **Career Constellation must remain exactly as it is now**. Do not redesign, regenerate, simplify, restyle, recolor, rearrange, or replace it.

---

## Reference files supplied with this brief

1. `resume2-full-page-reference.png`
   - Composition and layout reference for Resume 2.
   - Treat it as a visual target, not a source of literal text or fake data.
   - Use PeerSlate’s real data, existing interactions, and existing design tokens.

2. `resume2-blue-mountain-background.png`
   - Approved Resume 2 background direction.
   - Bright blue sky, white clouds, larger mountains, no people.
   - Optimize it for production rather than serving an unnecessarily large PNG directly.

The reference mockup’s Constellation is only a placeholder representation. **The implementation must reuse the real current Career Constellation already present on Resume 1.**

---

# 1. Inspect the existing implementation before writing code

Do not begin by creating a new isolated template from assumptions.

## Required discovery sequence

1. Run `git status` and record:
   - Current branch
   - Modified and untracked files
   - Whether work is already in progress

2. Start the current Flask application using the repository’s normal development command.

3. Open and inspect the existing page first:

   `http://127.0.0.1:5000/petec/resume`

4. Inspect it at minimum at:
   - 1920 × 1080
   - 1440 × 900
   - 1024 × 768
   - 390 × 844

5. Scroll through the complete page and test the existing behavior:
   - Career-ribbon/timeline selections
   - Ledger chapter updates
   - Evidence cards and skill interactions
   - Chapter links
   - PDF/download behavior
   - Contact and LinkedIn actions
   - Ask Pete AI entry point
   - Keyboard navigation
   - Focus states
   - Reduced-motion behavior
   - Current mobile behavior
   - Career Constellation interactions and animations

6. Trace the current implementation through the repository. Locate and read:
   - Flask route/controller for `/<profile>/resume`
   - Current résumé template and partials
   - Résumé CSS
   - Résumé JavaScript
   - Shared glass-card and design-system components
   - Profile résumé data source
   - Timeline/Ledger data model
   - Skills/evidence data source
   - Career Constellation template, CSS, JavaScript, and data
   - Existing mockups and approved résumé assets
   - Relevant tests
   - Any Storybook components associated with this experience

7. Search the repository using terms such as:
   - `resume`
   - `living resume`
   - `ledger`
   - `career constellation`
   - `timeline`
   - `evidence`
   - `skills`
   - `profile slug`
   - `petec`

8. Determine whether the route is already generic for multiple users. Follow the existing architecture.

## Architecture rule

PeerSlate is a **multi-user application**. Pete is fixture/demo content.

Do not hardcode Pete’s:
- Name
- Employers
- Dates
- Metrics
- Photo
- Contact details
- Education
- Skill evidence
- Career nodes

Resume 2 must render from the same structured profile data as Resume 1.

---

# 2. Routes and Resume 1 / Resume 2 comparison

## Required route behavior

Keep the current route intact:

`/<profile_slug>/resume`

Create a sibling route using the repository’s existing routing conventions:

`/<profile_slug>/resume2`

For the current fixture this should resolve as:

- Resume 1: `/petec/resume`
- Resume 2: `/petec/resume2`

Do not rename or redirect the existing Resume 1 route.

## Comparison switch

Add a compact page-local segmented switch labeled:

- `Resume 1`
- `Resume 2`

Requirements:

- Show it on both Resume 1 and Resume 2.
- Place it near the résumé page header/utility area.
- Do not add two noisy permanent links to the entire global site navigation.
- Resume 1 links to the existing résumé route.
- Resume 2 links to the new route.
- Use an unmistakable active state.
- Add `aria-current="page"` to the active option.
- Keep it keyboard accessible.
- Make it fit cleanly on mobile.
- Preserve the existing global navigation.

The only visual modification allowed on Resume 1 is the addition of this comparison switch and any tiny spacing adjustment strictly required to fit it.

---

# 3. Core visual direction for Resume 2

Resume 2 should feel:

- Larger
- Bolder
- More cinematic
- More editorial
- More spacious
- Less mechanically aligned
- Clearly part of Foundation C
- Easy for recruiters to scan

The layout must use **intentional asymmetry**, not random disorder.

Avoid making every section:
- The same width
- Centered on the same vertical line
- The same card shape
- The same internal grid
- Equally visually prominent

Every section should feel like a different room in the same building.

---

# 4. Background implementation

Use `resume2-blue-mountain-background.png` as the source artwork.

## Visual requirements

- No people
- Bright blue sky
- White clouds
- Large mountains occupying the lower portion
- Open sky behind upper content
- Mountains support the experience without obscuring text
- No visible image tiling or hard seams
- Do not stretch the source image vertically across the entire long page

## Recommended implementation

- Place the optimized image in a dedicated location such as:
  `static/images/mockups/resume2/`
- Create an optimized WebP or AVIF version, while retaining the source only if repository conventions permit.
- Use a fixed or sticky scenic backdrop layer for desktop.
- Use a safer absolute/pseudo-element backdrop strategy on mobile if `background-attachment: fixed` causes Safari issues.
- Use `cover` with a carefully selected focal point.
- Add subtle atmospheric overlays behind content:
  - Soft pale-blue/white wash
  - Slight edge vignette where needed
  - Localized contrast beneath major glass surfaces

Do not darken the entire page. It should remain a premium light experience.

The Career Constellation must retain its own existing dark treatment.

---

# 5. Foundation C requirements

Reuse the current design system. Do not invent an unrelated résumé theme.

## Typography

- Newsreader for major editorial headings
- Inter for UI, labels, metadata, and body copy
- Stronger heading scale than Resume 1
- Minimum comfortable body size around 15–16 px on desktop
- Generous line height around 1.5–1.65
- Do not use tiny text to force content into cards

## Approved color language

- Product Indigo: `#4F5BD5`
- Connection Azure: `#4EA3FF`
- AI Cyan: `#2EC8D3`
- Evidence Amber: `#D7A33E`
- Midnight Ink: `#0A1B36`
- Cloud White: `#F6F8FC`

Do not introduce:
- Pink
- Rose
- Magenta
- Coral semantic accents

## Glass surfaces

Content-heavy glass must be readable against bright clouds.

Use the current PeerSlate glass component where possible, with Resume 2 variants such as:

- Approximately 74–86% light surface opacity depending on content density
- Strong but restrained backdrop blur
- Thin white/blue border
- Soft layered shadow
- Slightly stronger contrast for body-copy panels
- Lighter transparency for decorative or navigation surfaces

Do not make the text sit directly over highly detailed background areas.

---

# 6. Page width and scale

The current implementation was visually too small on wide desktop screens. Resume 2 should use more of the viewport.

Recommended desktop composition:

```css
width: min(94vw, 1600px);
margin-inline: auto;
```

Use responsive fluid values rather than blindly copying fixed numbers.

General targets:

- Major content width: approximately 1450–1600 px maximum
- Larger Ledger
- Larger section headings
- More legible body text
- Larger timeline nodes
- More generous metric cards
- Background remains visible as framing, not as the dominant subject

---

# 7. Page structure and section requirements

Retain all current meaningful résumé content and functionality.

Recommended sequence:

1. Global navigation
2. Profile/identity stage
3. Career ribbon
4. Living Résumé Ledger
5. Experience
6. Education
7. Skills & Evidence
8. Development
9. Career Constellation — current implementation unchanged

Do not remove an existing section merely because the generated mockup did not show it clearly.

---

## 7A. Profile and identity stage

Use the real current profile content.

Create a bold, wide identity card anchored toward the upper left.

Include existing available fields such as:

- Profile image
- Name
- Current title
- Short professional summary
- Location
- Email/contact
- LinkedIn
- Résumé PDF
- Share/contact actions

Use a smaller secondary quotation or career-ribbon card offset to the right if the current data supports it.

The profile composition should be deliberately asymmetric:
- Main identity block carries most of the weight
- Secondary quote/contact information is offset and smaller
- Do not split the screen into two identical rectangles

Keep all content data-driven.

---

## 7B. Career ribbon

Preserve the current timeline meaning and selection behavior.

Refine its presentation for Resume 2:

- Larger nodes
- Strong active node
- More horizontal breathing room
- Clear labels and dates
- Connected line remains visually continuous
- Nodes may vary subtly by importance and active state
- It should feel like part of the story, not a detached navigation widget

Selecting a career node must continue to update the Ledger in-frame.

Do not duplicate state logic if existing shared logic can be reused.

---

## 7C. Living Résumé Ledger

The Ledger is the dominant product experience.

### Composition

- Float the chapter/navigation rail slightly left of the main Ledger
- Let it overlap or sit offset rather than aligning perfectly with every lower section
- Main Ledger should be wide and visually commanding
- Use a strong editorial chapter title
- Use actual selected-role content
- Use current chapter image/media rules
- Keep evidence and metrics highly visible

### Visible information

- Current selected chapter
- Employer/organization
- Role
- Dates
- Concise chapter summary
- Five or fewer primary metrics where possible
- Selected evidence cards
- Clear chapter-detail action

### Interaction

- Timeline selection updates the Ledger without navigating away
- Existing keyboard behavior remains
- Focus management remains correct
- Shared data remains the source of truth

Do not create a separate fake set of Ledger data for Resume 2.

---

## 7D. Experience

Use a cinematic chapter-gallery composition inspired by the reference.

Requirements:

- Show the major roles as large chapter cards
- Use three visible cards on wide desktop when data permits
- Use no more than three or four primary bullets per collapsed card
- Emphasize the strongest measurable outcomes
- Provide `View Chapter` or equivalent actions
- Allow more detail to open in place or connect back to the Ledger
- Do not present every résumé bullet at once
- Avoid a dense wall of tiny text

Intentional asymmetry options:

- Section may be slightly wider than Skills
- One selected chapter can be subtly larger
- Cards can use controlled vertical offsets of approximately 12–28 px
- Section header need not align exactly with the Ledger title

Do not use arbitrary rotations that reduce professionalism or accessibility.

---

## 7E. Education

Retain the current Education content and interaction.

Give Education a quieter editorial treatment so it does not look like another copy of Experience.

Suggested composition:

- One large primary education card
- One or two smaller supporting cards offset beside or below it
- Clear degree, institution, dates, and significance
- Evidence or trajectory note where data supports it
- Maintain comfortable reading width

Do not fabricate degrees, institutions, dates, or claims.

---

## 7F. Skills & Evidence

Replace a flat grid of equally weighted skill tiles with an evidence explorer.

Recommended desktop layout:

1. Category selector
2. Skills within the active category
3. Shared evidence detail panel

Example category language, only where supported by current data:

- Systems Engineering
- Program & Lifecycle Management
- Digital, Data & AI

Interaction requirements:

- Selecting a category updates the visible skills
- Selecting a skill updates one shared evidence panel
- Show approximately two or three strongest proof points initially
- Preserve access to complete evidence
- Use current skill/evidence data
- Keep keyboard support and visible focus
- Announce meaningful dynamic updates appropriately where existing accessibility patterns permit

Do not hardcode a new Pete-only skills matrix.

---

## 7G. Development

Present development as a forward-looking roadmap.

Use a row or staggered sequence of large cards for current items such as:

- Certifications
- MBSE learning
- Ph.D. development
- AI/data learning

Only render items actually present in the current profile data.

On desktop:
- Use a wide horizontal composition
- Allow controlled offsets between cards
- Preserve generous whitespace

On mobile:
- Stack or use accessible horizontal snapping
- Do not require precision dragging
- Keep all content reachable by keyboard and touch

---

## 7H. Career Constellation — protected section

This requirement is absolute.

Reuse the current real Career Constellation from Resume 1.

Do not change its:

- Internal layout
- Node positions
- Curves
- Colors
- Typography
- Metrics
- Background
- Labels
- Animation
- Interaction
- Data behavior
- Visual hierarchy

Do not rebuild it from the generated reference image.

Prefer rendering the exact same shared partial/component and loading the exact same CSS/JavaScript.

A minimal outer wrapper or page-level spacing adjustment is acceptable only when needed to place the unchanged Constellation cleanly within Resume 2.

Before completing the task, compare Resume 1 and Resume 2 side by side and verify the Constellation itself is visually identical.

---

# 8. Intentional asymmetry rules

The user wants the page to feel less perfectly aligned.

Apply asymmetry with restraint:

- Offset the Ledger rail from the main card
- Alternate section widths between approximately 88% and 96% of the main container
- Shift some sections 1–3% left or right
- Use varied card spans
- Let one card in a group carry more emphasis
- Vary top spacing between acts
- Keep a clear underlying grid

Do not:

- Randomly scatter content
- Rotate body-copy cards
- Create inaccessible reading order
- Make the DOM order differ from the visual reading order
- Cause horizontal overflow
- Sacrifice recruiter scanability

The design should look composed, not accidental.

---

# 9. Navigation and fixed controls

## Internal chapter navigation

Resume 2 may use the current résumé side navigation as a base, refined into a museum-like chapter guide.

Requirements:

- Clear active section
- Less visual weight than the Ledger
- Sticky only where it does not cover content
- Collapses cleanly on tablet/mobile
- Keyboard accessible
- Correct scroll-spy behavior
- Respect reduced motion

## Ask Pete AI

Keep Ask Pete AI available.

- Prevent overlap with cards and the Constellation
- Respect bottom and right safe-area insets
- It may become a compact orb during scroll if an existing supported pattern allows it
- Do not alter its underlying route or behavior

---

# 10. Motion

Motion should feel calm and expensive.

Use restrained motion such as:

- Soft fade/translate reveals
- Timeline active-state transition
- Evidence-panel crossfade
- Gentle glass elevation on hover
- Subtle background depth only if performance remains strong

Recommended timing:
- Small UI state changes: approximately 160–220 ms
- Card transitions: approximately 240–360 ms
- Section reveals: approximately 350–500 ms

Avoid:

- Bouncy easing
- Fast spinning
- Continuous distracting animation
- Heavy scroll-jacking
- Large parallax movement
- Motion that delays access to content

Honor `prefers-reduced-motion`.

---

# 11. Responsive behavior

## Tablet

- Preserve the identity hierarchy
- Allow career ribbon horizontal scrolling or snapping when necessary
- Convert the side rail to a compact sticky chapter control
- Maintain readable Ledger metrics
- Keep section offsets subtle

## Mobile

Target at least 390 × 844.

Requirements:

- No horizontal page overflow
- Identity content stacks logically
- Resume 1 / Resume 2 switch remains visible and usable
- Career ribbon becomes accessible horizontal snap/scroll or a compact chapter selector
- Ledger becomes full width
- Metrics use one or two columns depending on available width
- Experience becomes a single-card sequence or stack
- Education stacks in reading order
- Skills categories, skills, and evidence stack vertically
- Development cards stack or snap
- Ask Pete AI does not cover controls
- Preserve the current Career Constellation mobile treatment

Do not merely shrink the desktop layout.

---

# 12. Accessibility

Meet or improve the current page’s accessibility.

Required:

- Semantic heading order
- Logical DOM and tab order
- Visible focus states
- Keyboard-operable timeline and skill controls
- Appropriate buttons versus links
- `aria-current` for Resume 1 / Resume 2
- Meaningful image alt text or decorative empty alt where appropriate
- Sufficient contrast over glass and clouds
- Reduced-motion support
- Touch targets approximately 44 × 44 px where possible
- No information conveyed by color alone
- Dynamic evidence changes remain understandable to assistive technology

---

# 13. Performance

- Optimize the supplied background into modern formats
- Use responsive image techniques where practical
- Avoid loading two full résumé implementations on one route
- Reuse current components and data
- Avoid duplicate large JavaScript bundles
- Prevent cumulative layout shift
- Lazy-load noncritical section imagery
- Do not lazy-load the primary hero image if doing so causes visible delay
- Confirm the background strategy performs acceptably on mobile

---

# 14. Existing behavior that must not break

Do not break:

- Resume 1
- Existing résumé PDF behavior
- Existing profile routing
- Existing profile/data loading
- Current timeline and Ledger state behavior
- Current skill/evidence behavior
- Current Career Constellation
- Ask Pete AI
- Global navigation
- Authentication/identity behavior
- Tenant safety
- Existing database behavior
- Existing production routes
- Current approved design-system components

No database schema change should be necessary for this visual comparison page.

---

# 15. Suggested implementation strategy

Prefer composition and reuse over duplication.

A good architecture may be:

- Shared résumé data/view model
- Shared functional partials/components
- Resume 1 page composition
- Resume 2 page composition
- Shared Career Constellation partial
- Resume 2-specific layout stylesheet scoped under a root class such as:
  `.resume-v2`
- Small shared version-switch partial
- Shared résumé interaction module where possible

Do not globally override Resume 1 styles.

All Resume 2 CSS should be scoped to the Resume 2 root or use an equivalent isolation strategy.

---

# 16. Verification and screenshots

Before reporting completion:

1. Compare Resume 1 and Resume 2 side by side.
2. Confirm Resume 1 has not visually changed except for the version switch.
3. Confirm Resume 2 uses the approved no-people background.
4. Confirm all real résumé data is present.
5. Confirm all interactive states work.
6. Confirm the Career Constellation is identical between versions.
7. Confirm no horizontal overflow.
8. Confirm focus and keyboard behavior.
9. Confirm reduced motion.
10. Confirm PDF and AI actions.
11. Confirm generic profile routing.

Capture screenshots in a dedicated artifact directory, following repository conventions, for example:

- `resume2-desktop-1920x1080-top.png`
- `resume2-desktop-1440x900-ledger.png`
- `resume2-desktop-full-page.png`
- `resume2-mobile-390x844-top.png`
- `resume2-mobile-390x844-skills.png`
- `resume1-resume2-comparison.png`
- `resume1-constellation.png`
- `resume2-constellation.png`

Also provide a short screen recording showing:

- Switching from Resume 1 to Resume 2
- Timeline selection
- Ledger update
- Skill evidence update
- Scrolling into the unchanged Career Constellation
- Mobile layout

---

# 17. Completion report

When finished, report:

1. Current branch and final commit hash, if a commit was requested/performed
2. Routes added or changed
3. Files created
4. Files modified
5. Shared components reused
6. Resume 1 changes
7. Resume 2 implementation summary
8. Background optimization details
9. Confirmation that the Career Constellation was not changed
10. Tests run and results
11. Screenshot/video artifact locations
12. Any remaining limitations or recommendations

Do not claim a requirement is complete unless it was tested.

---

# Final acceptance criteria

Resume 2 is accepted when:

- `/petec/resume` remains Resume 1
- `/petec/resume2` renders the alternate design
- Both pages display an accessible Resume 1 / Resume 2 comparison switch
- Resume 2 looks recognizably like the supplied full-page reference
- Resume 2 is visibly larger and bolder than Resume 1
- The layout uses intentional offsets and controlled asymmetry
- The supplied blue-sky/large-mountain/no-people background is used
- Existing résumé data and functionality are preserved
- The page remains multi-user and data-driven
- Education is retained
- Skills use an evidence-explorer presentation
- Experience is more scannable
- Development feels forward-looking
- The current Career Constellation is reused unchanged
- Desktop, tablet, mobile, keyboard, and reduced-motion states work
- Resume 1 is not replaced or materially altered

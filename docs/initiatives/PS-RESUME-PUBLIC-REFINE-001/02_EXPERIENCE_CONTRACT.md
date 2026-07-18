# PS-RESUME-PUBLIC-REFINE-001 — Experience and Accessibility Contract

## Default scan

- Retain a single clear name, role/positioning statement, short summary, and concise action group.
- Consolidate duplicate Ask AI and résumé actions when the same action appears more than once in the opening. A persistent contextual action may remain if its purpose is distinct and accessible.
- Keep impact evidence scannable and linked to supporting experience.
- Show a compact skills overview; reveal two or three strongest approved proof points for the selected capability rather than expanding every source by default.
- Keep experience chapters and credential records available through explicit disclosure. Do not remove approved details from the underlying HTML/data contract merely to make the page shorter.
- Preserve the constellation as the same-data career relationship view below the primary résumé reading path.

Claude Code may choose the exact grouping and disclosure pattern after inspecting the live page and tests, provided the result meets the contract and stays within reserved files.

## Interaction requirements

- Use native controls or button semantics for disclosure; no clickable generic containers.
- Every toggle exposes accurate `aria-expanded` and `aria-controls`; hidden panels are not focusable.
- Opening a panel announces useful status and moves focus only when that improves context. Closing restores focus to the initiating control.
- Hash links and section ribbon navigation continue to reach meaningful headings.
- The document remains understandable when JavaScript fails; essential public meaning must not depend on animation.
- Honor `prefers-reduced-motion`; motion should use transform/opacity and never be required to understand state.

## Responsive requirements

- Test at representative 1440×900 and 1920×1080 desktop viewports and at least 390×844 mobile.
- At 200% zoom, content reflows without two-dimensional scrolling for normal reading.
- Mobile uses readable document flow; do not shrink the desktop visualization until labels become illegible.
- Focus indicators and contrast remain WCAG 2.2 AA targets.

## Data and truth requirements

- Render only the existing approved public résumé fields supplied by the route.
- Keep generic loops/view models; do not hardcode Pete’s employers, dates, metrics, role counts, education, or skills into reusable behavior.
- Run the existing multiple-fixture tests to ensure the page is not accidentally Pete-only.
- Preserve the ATS-friendly PDF/download path and canonical/redirect behavior.

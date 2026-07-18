# PS-INTERVIEW-PUBLIC-GATE-001 — Experience and Accessibility Contract

## Progressive opening

The first viewport should answer four questions without requiring a settings tour:

1. Is this public or private? Public demonstration.
2. Who is the profile in view? The named public profile.
3. What can I do first? Start one written practice answer or choose another clearly labeled mode.
4. Where will my work go? Browser-local until I explicitly submit an answer for coaching; no account sync.

Keep one dominant practice object. Experience level, question family, session length, queue, settings, history analytics, and explanatory depth may remain available, but should not compete equally with the active question.

## Truth labels must remain visible

Progressive disclosure may simplify the page, but it must not hide the public-demo label, current grounding mode, browser-storage boundary, or submit/transmission disclosure behind a settings dialog. Longer explanations may be disclosed from a short accurate label.

## Interaction requirements

- Tabs, disclosure controls, dialogs, and mode switches expose correct names, roles, selected/expanded states, and focus behavior.
- Disabled or unavailable modes explain why and offer a real fallback.
- Dialog opening moves focus to a useful element; closing returns focus to the trigger.
- Status and error messages use the existing live region without repeated or misleading announcements.
- Browser-history navigation and deep links continue to restore the intended public view.
- Deleting or clearing browser-local records remains explicit and accurately scoped.

## Responsive and media requirements

- Review at 1440×900, 1920×1080, and 390×844, plus 200% zoom.
- Do not shrink tabs, question text, forms, or feedback until they become unreadable. Stack and disclose instead.
- Camera denial, missing camera, missing speech recognition, local-storage failure, and request failure must preserve a typed practice path.
- Honor `prefers-reduced-motion`; no essential state depends on animation.
- Essential public/private meaning remains in the server-rendered HTML when JavaScript fails.

## Copy guardrails

- Prefer “public profile,” “approved public history,” “this browser,” and “sent for coaching when submitted.”
- Avoid “your private history,” “saved to your account,” “secure recording,” or “synced” because those capabilities are not implemented here.
- Replace ambiguous “proof” language with “relevant history” or “sources used” where needed.
- Do not introduce voice-Capture language. Dictation inside public practice is not the private Capture system.

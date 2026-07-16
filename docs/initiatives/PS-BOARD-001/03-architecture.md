# 03 — Information Architecture

## Page hierarchy

```text
Real PeerSlate global shell
└─ Slate Board page
   ├─ title / concise board actions
   └─ living-whiteboard workspace
      ├─ labeled control rail
      ├─ physical board frame
      │  ├─ Short Term
      │  ├─ Projects
      │  ├─ Long Term
      │  └─ Work
      ├─ marker tray / Chalk It Up
      ├─ Board/List equivalent view
      └─ contextual layers
         ├─ capture/listening
         ├─ proposal review
         ├─ note editor
         ├─ Focus panel
         └─ audience preview
```

The global shell, public/member Slate navigation, and Board controls are
separate levels. This package must not add another permanent navigation layer.

## Rendering boundaries

- Flask/Jinja provides routes, trusted configuration, fixture/bootstrap state,
  and shared shell integration.
- Semantic HTML owns headings, controls, notes, lists, dialogs, labels, and
  accessible state.
- Scoped CSS supplies Photo 1's room, board, aluminum frame, paper, handwriting,
  shadows, tray, and responsive reflow.
- JavaScript controls local interaction state, editing, movement, view switching,
  focus return, and honest prototype workflows.
- SVG or CSS may draw quadrant and connector lines. Meaningful text must remain
  semantic DOM content.
- A future service layer, not AI or the browser, will enforce authenticated
  ownership, visibility, publication, audit, and idempotency.

## Owner and public modes

The long-term owner Board belongs in a protected workspace with editing tools.
The public Slate Board is a read-only, audience-filtered projection of explicitly
published canonical records. They may share visual components, but the public
mode must not receive owner tools, raw captures, private notes, transcripts, AI
drafts, private comments, or unpublished goals.

The current route remains a preview baseline until protected owner/public modes
and their tests exist. Visual polish must not be described as that separation.

## Shared object rule

Ledger, Journal, Work, Story, future Goals, and Board views should eventually
project the same canonical records. Board placement is presentation metadata;
it must never become a second copy of a project's title, evidence, progress, or
visibility.

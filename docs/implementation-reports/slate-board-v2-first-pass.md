# Slate Board v2 first pass

- **Branch / commits:** `codex/slate-board-v2`; `843f368 PS-BOARD-V2: add Slate Board preview` (based on `ceba528` preflight).
- **Preview route:** `/_internal/slate-board-v2` — local-only unless `ENABLE_DESIGN_SYSTEM_PREVIEW=1`; current `/slate-board` and `/petec/slate-board` are unchanged.
- **Changed files:** `app.py`, `templates/slate_board_v2.html`, `static/css/slate-board-v2.css`, `static/js/slate-board-v2.js`, and `tests/test_slate_board_v2_preview.py`.

## Implemented

- Whiteboard-first opening object with four independently scrollable, hand-placed fixture note lanes: Short Term, Projects, Long Term, and Work.
- Concise permanent controls: Add to Board, AI Help, Connections, and More.
- Fixture-backed five-state Add-to-Board flow using “Study for the PMP certification”: capture, details/privacy, note added, AI guidance, and people matching.
- Types, color, handwriting, and visibility are represented in the details state; the fixture defaults to private.
- AI and matching are explicitly proposal/opt-in presentation states only. No people query, save, connection, or backend privacy assertion occurs.
- Accessible structured list alternative, visible focus, and reduced-motion rules. Focus Stage is absent and remains off by default.

## Fixture-only / deferred

- Board items and modal state are static browser fixtures; persistence, edit/delete, server validation, dates, visibility enforcement, AI resources, matching, and tenant-safe models require backend work.
- The current production Board remains the only existing functional local-storage Board.

## Validation

- `ANTHROPIC_API_KEY=test-preview-key C:\Users\peter\Documents\portfolio\venv\Scripts\python.exe -m unittest tests.test_slate_board_v2_preview` — passed (1 test).
- Existing Flask route baseline was already 200 for `/slate-board` and `/petec/slate-board`.
- `git diff --check` passed before commit.
- Browser review: desktop Board and the capture state of the five-step dialog were inspected; the accessible list is exposed in the document structure. A 390×844 capture was attempted; narrow-view rendering needs a second visual QA pass before review approval.

## Review tomorrow

1. Start the app in this worktree and open `http://127.0.0.1:5052/_internal/slate-board-v2`.
2. Open Add to Board and progress through all five states.
3. Toggle the structured list and keyboard-check its control.
4. Recheck at 390×844, 1440×900, 200% zoom, and reduced motion before sign-off.

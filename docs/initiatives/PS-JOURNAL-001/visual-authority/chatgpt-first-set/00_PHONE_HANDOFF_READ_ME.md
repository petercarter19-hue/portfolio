# PeerSlate Journal Visuals — Phone Handoff

## Confirmed approach

Use a small task-specific visual-authority packet, not the complete Bible,
Roadmap, research archive, or every PeerSlate reference image in one ChatGPT
conversation.

For this first generation round, ChatGPT needs:

1. one self-contained PeerSlate and Journal context block;
2. one exact first-set generation prompt;
3. three approved reference images with clearly different roles;
4. the required screen/state matrix; and
5. a review-and-revision checklist.

This approach is confirmed against Bible v2.8, Roadmap v2.7,
`PS-JOURNAL-001`, the Owner Visual Integrity Standard, the Owner Story
Composition Standard, and current OpenAI image-generation guidance. A small,
explicitly mapped reference set is easier to control than a large undifferentiated
upload. The full Bible and Roadmap remain implementation authority, but their
relevant first-set instructions have been distilled into phone-readable text
in this folder.

## Important status boundary

This folder is a **briefing package**, not an accepted visual authority and not
evidence that Journal is implemented or live.

The four first-round images establish composition, interaction hierarchy, and
visual language. They are not the complete V1 design set. Later rounds must
still cover Voice processing/review, failures, owner management/detail/
curation, all authorized viewer modes, long history, empty/restricted states,
200% reflow, visible focus, reduced motion, and the remaining Home/Studio
origin contexts before implementation can pass the visual entry gate.

## Fastest phone workflow

1. Open the Azure DevOps `portfolio-site` repository on branch `main`.
2. Browse to:
   `docs/initiatives/PS-JOURNAL-001/visual-authority/chatgpt-first-set/`.
3. Download the three images listed in
   `04_REFERENCE_IMAGE_MANIFEST.md` from
   `docs/governance/approved_owner_visual_baseline/`.
4. Start one new ChatGPT Images conversation for this Journal package.
5. Upload the three images in the exact order in the manifest.
6. Copy all text from `01_COPY_PASTE_PEERSLATE_CONTEXT.txt` into ChatGPT.
7. Copy all text from `02_COPY_PASTE_FIRST_SET_PROMPT.txt` into the same
   conversation.
8. Have ChatGPT generate **JOURNAL-01 only**. Review it before requesting the
   next image.
9. Use `05_REVIEW_AND_REVISION_PROMPTS.txt` to correct drift one issue at a
   time.
10. After JOURNAL-01 is accepted as the working direction, generate
    JOURNAL-02, JOURNAL-03, and JOURNAL-04 in the same conversation so ChatGPT
    can preserve the accepted shell and visual language.
11. Download each accepted result and preserve the names from the screen
    matrix.

## If only text can be accessed

The two copy/paste text files are self-contained for product behavior and
visual direction. Do not paste the entire Bible or Roadmap after them; doing so
can reintroduce older or unrelated product detail. The three reference images
are still strongly recommended because they communicate the approved finish,
material quality, rhythm, and editorial character more accurately than words
alone.

If the reference images are temporarily unavailable, ChatGPT may produce a
rough composition study, but label it **exploratory only**. It cannot become
PeerSlate visual authority until the exact images are supplied and parity is
reviewed.

## What not to give ChatGPT for this round

- Superseded Bible or Roadmap versions.
- The three research reports used to form the product strategy.
- Owner Home, Photo, Interview Studio, Slate Board, or résumé implementation
  packages.
- All five owner visual boards at once.
- Current production screenshots as if they were the Journal target.
- Instructions that invent final navigation, routes, public sharing, automatic
  AI changes, a Capture destination, or an Add to Journal step.

## Output discipline

Save accepted images as:

- `journal-v1-01-owner-journal-desktop.png`
- `journal-v1-02-universal-composer-desktop.png`
- `journal-v1-03-universal-composer-mobile.png`
- `journal-v1-04-saved-from-story-desktop.png`

Generated UI text is a visual reference, not source code or final production
copy. Engineers must recreate the accepted composition with real accessible
HTML and exact approved labels. Do not ship generated screenshots as the
working application.

## Authority priority for this handoff

If anything appears to conflict, use this order:

1. `01_COPY_PASTE_PEERSLATE_CONTEXT.txt` for current product truth.
2. `03_SCREEN_SET_AND_STATE_MATRIX.md` for required states and exclusions.
3. `02_COPY_PASTE_FIRST_SET_PROMPT.txt` for the requested generation round.
4. The three attached images for visual character only, as mapped in the
   manifest.
5. ChatGPT's creative suggestions last.

ChatGPT may propose improvements, but it must identify them rather than
silently changing the product contract.

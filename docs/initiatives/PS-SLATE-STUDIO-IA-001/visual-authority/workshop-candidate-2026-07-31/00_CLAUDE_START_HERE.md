# PeerSlate Workshop — Claude AI handoff

**Date:** 2026-07-31  
**Owner:** Pete Carter  
**Package type:** product-direction and visual-review handoff  
**Implementation authority:** none  
**Visual-lock status:** candidate set complete; Pete has not yet hash-locked the set for implementation

## Read first

This package transfers the newest Workshop direction and its five-screen visual sequence to Claude for an independent product, interaction, trust, and consistency audit.

It does **not** authorize Claude to implement code, edit the repository, create a competing visual direction, merge, deploy, rename live products, or represent any mockup behavior as implemented or live.

The newest owner direction in this package deliberately resets parts of the older Workshop/Slate Studio discussion. It is newer conversation-level product direction, but it has not yet been reconciled into repository governance. Preserve that distinction.

## What Claude should do

1. Read every Markdown file in this package and inspect all six images in `images/`.
2. Restate the product model and the five-screen workflow in concise language before evaluating it.
3. Audit the set for:
   - workflow continuity;
   - information hierarchy and professional polish;
   - component and copy consistency;
   - privacy, provenance, member control, and AI proposal boundaries;
   - state clarity and truthful downstream-use behavior;
   - accessibility and future responsive implications;
   - contradictions with the stated product direction.
4. Produce a prioritized mismatch register using `Critical`, `Material`, and `Polish` severity.
5. Separate:
   - non-material corrections that could later be implemented within a locked visual;
   - material visual changes that must return to ChatGPT and Pete;
   - product/architecture decisions that require Pete.
6. Produce an implementation-ready interaction specification only at the behavioral level. Do not write code or modify repository files.
7. End with no more than five questions whose answers would materially change the direction.

## Required stopping point

Stop after the audit, mismatch register, interaction specification, and material questions. Wait for Pete. Do not create new mockups or begin implementation.

## Visual sequence

1. `01-workshop-opening.jpg`
2. `02-workshop-type-speak.jpg`
3. `03-workshop-ai-review.png`
4. `04-workshop-saved-privately.png`
5. `05-workshop-my-information.png`

`00-reference-current-interview-studio.jpg` is a quality and interaction benchmark only. It is not Workshop content authority.

## Current verified repository boundary

- Azure DevOps `origin/main` verified at `2494aa73ed95bfbe97d8cf42f712b9929759e0b2` on 2026-07-31.
- Active package: `PS-SLATE-STUDIO-IA-001`.
- Current baseline status: `visual_direction_only_no_runtime_authority`.
- The local primary checkout was on `work/2026-07-25-entry-doc-corrections` with unrelated untracked content. It was treated as read-only.
- No repository files, branches, commits, routes, runtime behavior, flags, or governance documents were changed to create this handoff.


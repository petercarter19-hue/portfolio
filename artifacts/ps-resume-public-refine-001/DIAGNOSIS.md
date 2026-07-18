# PS-RESUME-PUBLIC-REFINE-001 — Hierarchy & default-scan diagnosis

_Recorded against the live DOM at `origin/main` base `6f9f22c34d791dac2466a957450dfc18e9285176`, measured headless at 1440×900, 1920×1080, 390×844._

## Measured BEFORE baseline (document scrollHeight)

| Viewport | scrollHeight |
|---|---:|
| 1440×900 | 5419 px |
| 1920×1080 | 5636 px |
| 390×844 (mobile) | 14219 px |

Section tops @1440: summary 140, impact 775, skills 1289, experience 1962, credentials 2966, constellation 4111, story 4982.
Repeating blocks @1440: experience cards 735 px ×3; credential cards 640 px ×4.

## Repeated hierarchy in the opening viewport

1. **"Ask Pete AI" appears three times** above the fold: the AI-panel kicker (the actual Ask experience), a filled primary **Ask Pete AI** button in the identity actions, and the sticky ribbon **Ask Pete AI** link — plus the AI panel's own **Ask** submit button. Four Ask surfaces competing in one viewport.
2. **Résumé/PDF appears twice** in the opening: identity **View Résumé** and ribbon **Résumé PDF**.
3. **Positioning is stated twice**: the role line "Systems Engineer & Technical Leader" is immediately echoed word-for-word by the tags line "SYSTEMS ENGINEER · TECHNICAL LEADER · MBSE, SUSTAINMENT, AND REQUIREMENTS".

## Long default scan below the opening

- **Experience**: three tall (735 px) cards each show role summary **plus** a "Selected impact" pair **plus** two accomplishment bullets **plus** a footer — before any deliberate "View Full Chapter". The two preview bullets are a strict subset of `resume2_full_record_bullets` (accomplishments + responsibilities), so they are already repeated inside the on-demand chapter.
- Section rhythm is airy: `.r2-content` inter-section gap up to 3rem, `.r2-section` padding up to 3rem, `.r2-section-heading` margin up to 2.4rem, impact tiles 11rem tall, constellation/story gaps up to 5rem.

## Refinement approach (spacing / grouping / collapsed optional depth — no type shrink, no lost meaning)

- Opening: keep one identity + one dominant next action (the Ask panel). Remove the duplicate identity **Ask Pete AI** button (Ask stays served by the persistent ribbon control and the inline panel). De-duplicate the tags line to the descriptors not already in the role line. Retain **View Résumé** and **Contact** as the two distinct secondary actions, and keep the ribbon's persistent Ask + Résumé PDF.
- Experience: default preview becomes role summary + Selected impact; the two accomplishment bullets move to the on-demand full chapter only (they already render there). Depth reachable via the existing accessible "View Full Chapter" disclosure.
- Rhythm: tighten inter-section gap, section padding, heading margins, identity vertical spacing, impact tile height, and constellation/story gaps.
- Skills already reveal only the strongest approved proof points on demand — left intact.

Target: ≈8–9% perceived desktop compression, evidenced by measured scrollHeight reduction, while preserving meaning, data, canonical route/redirects, Ask AI, contact, ATS/PDF path, and the Career Constellation.

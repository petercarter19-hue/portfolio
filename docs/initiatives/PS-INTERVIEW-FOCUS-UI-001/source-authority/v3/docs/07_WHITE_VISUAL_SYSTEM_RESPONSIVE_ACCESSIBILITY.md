# 07 — White Visual System, Responsive Behavior, and Accessibility

## Locked light-theme direction

The foundation is **clean white**. Do not use beige, cream, ivory, parchment, tan, sepia, or paper-texture backgrounds.

Recommended semantic reference values for visual matching; map them to existing production tokens where possible:

| Role | Reference |
|---|---|
| Page canvas | `#FFFFFF` |
| Primary surface | `#FFFFFF` |
| Secondary surface | `#F6F8FC` |
| Primary ink | `#10213B` |
| Deep navy | `#0B2C52` |
| Cobalt accent / primary emphasis | `#2E5FD4` |
| Cobalt soft | `#E8EEFF` |
| Teal status/support | `#0F7A72` |
| Teal soft | `#E3F3F1` |
| Muted text | `#64748B` |
| Borders | `#DCE3ED` |
| Error/destructive | `#B54747` |
| Error soft | `#FDECEC` |

Use cobalt for active navigation, selected answer basis, progress, and primary emphasis. Use teal for truthful save/generation/device/success support. Use red only for real error or destructive media actions. Do not recreate the old gold/beige atmosphere.

## Dark theme

Use one semantic DOM and state system. Dark mode uses deep navy surfaces, off-white text, cobalt highlights, and teal status. It is a token swap, not a redesign. Recording/destructive/error meanings remain clear without relying on color alone.

## Responsive breakpoints as behavior, not device labels

- Wide desktop: mode-specific main stage + rail.
- Narrow desktop/tablet: reduce rail width, then convert rail to drawer/sheet when it would crush the task.
- Mobile portrait: single-column task, compact sticky question summary after scroll, supporting content in bottom sheets/disclosures, reachable primary action.
- Mobile landscape: text controls, camera controls, recording stop/discard, and sheets remain reachable without covering the task.
- Interview AI: selected answer basis and source label remain visible when the rail collapses.
- Video Practice: preview remains dominant; device settings move to a sheet; transcript keyboard does not cover submission.

## Accessibility requirements

- Real textarea/input and native media controls where possible.
- Logical heading/landmark order.
- Visible keyboard focus; focus may not be hidden under sticky UI.
- Minimum touch targets according to repository standard, aiming for 44×44 where practical.
- 200% zoom without horizontal page scrolling for the core task.
- 320 CSS px reflow.
- Reduced-motion support.
- Focus trap and return for modal/drawer/sheet UI.
- Inactive future states removed from accessibility tree.
- Autosave/listening/generation/coaching/device/recording/error announcements are concise and nonrepetitive.
- Recording timers are not announced every second.
- Answer-basis selection uses semantic radio behavior and textual labels.
- Device and recording states do not rely on color alone.
- Verify color contrast using implemented tokens, not screenshots alone.

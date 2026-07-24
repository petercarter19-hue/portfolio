# Slice 1 visual direction asset manifest

**Package:** `PS-SLATE-STUDIO-IA-001`
**Owner review date:** 2026-07-23
**Status:** Owner-accepted direction evidence. These files are design mockups,
not implementation screenshots, browser evidence, or proof of live behavior.

The original concept/material authority remains the exact hash-pinned desktop
pair one directory above. This folder preserves the later Slice 1 responsive
and state adaptations reviewed with Pete. The adaptations control intended
component order, state wording, responsive reflow, and light/dark parity for a
future implementation package. They do not activate that package.

## Responsive and accessibility-direction set

| File | Intended review condition | Dimensions | SHA-256 |
|---|---|---:|---|
| `desktop-light-not-connected.jpg` | Desktop, light, not connected | 853 x 1280 | `639F4A30D4D807E9B579C410478E9F06B34C06011C85792EB6F128A574BEDDAE` |
| `desktop-dark-not-connected.jpg` | Desktop, dark, not connected | 853 x 1280 | `D9BD593D0703A80C4A47BDDD6EDEA667B384867B876A2B3F77A4CCE8FCBBBA8D` |
| `tablet-light-not-connected.jpg` | Tablet, light, stacked introduction/status | 773 x 1280 | `FE64E417AB49354A580E4849DAE63784BB65335894F015B79D8DFE4F6ADA94E4` |
| `tablet-dark-not-connected.jpg` | Tablet, dark, stacked introduction/status | 767 x 1280 | `42472928A5C7DD7705815420EADDF1BC876CBE958282065CF839DBDE6ED97144` |
| `mobile-390-light-not-connected.jpg` | 390 CSS px mobile direction, light | 592 x 1280 | `6CDEE42601E130CE3C93B4FFD395ADD7DF3CE677F7E117FDFE26630C7BC6ADF4` |
| `mobile-390-dark-not-connected.jpg` | 390 CSS px mobile direction, dark | 647 x 1280 | `3D2C49296EF1D4D7F69BF5DC243B8176D7CDE390EE642EBC1576A2CCF9E6438E` |
| `mobile-320-light-not-connected.jpg` | 320 CSS px narrow-mobile direction, light | 600 x 1280 | `1632486B3DBFD0F54AF9FE91CA93B338F55B1CD7B940EA4A4CC2169700EF7AF5` |
| `mobile-320-dark-not-connected.jpg` | 320 CSS px narrow-mobile direction, dark | 621 x 1280 | `0156C9197D92A60FE610B4FE1DCB34774F05D7841E19741E2669472EA2E3D0B7` |
| `short-landscape-light-not-connected.jpg` | Short landscape, light | 1280 x 590 | `BC4C3B3E3CA622E2AD66435DA1CDB619D65EC1EE141C8950C998D911994B0DB2` |
| `short-landscape-dark-not-connected.jpg` | Short landscape, dark | 1280 x 604 | `ACD8DEE3CA76E309051B119F6A6F49746A4369DA765977C2E756114ED65D4C3E` |
| `reflow-200-focus-light-not-connected.jpg` | Narrow/200% reflow direction with visible link focus, light | 546 x 1280 | `EEBAC6940CED6B7D44152F8311F6247C68FA8C0DFBA27A83E34030FAD55023DE` |
| `reflow-200-focus-dark-not-connected.jpg` | Narrow/200% reflow direction with visible link focus, dark | 546 x 1280 | `506C15C19EF1C67A027B94E538D2CFADC36A9AE31A4117B98F2024629163BF97` |
| `forced-colors-not-connected.jpg` | Forced-colors direction and focus visibility | 607 x 1280 | `1E0FC7E2B36F5E73744FC0C6C52A6C36EC317563C3A77B93F80A5BDFEE6E07F0` |

The physical pixel dimensions above identify the preserved files. The viewport
names identify the responsive condition each mockup was designed to represent;
they are not claims that an image generator produced exact browser CSS pixels.
Real viewport, zoom, touch-target, contrast, keyboard, assistive-technology,
and no-horizontal-scroll evidence remains an implementation obligation.

## State-direction set

| File | State | Dimensions | SHA-256 |
|---|---|---:|---|
| `loading-light.png` | Loading, light | 1024 x 1536 | `CFE759DD801ADE67C494E1E9E14259F9A23BB320B96C338AE94D216B4E9AE1D3` |
| `loading-dark.png` | Loading, dark; final owner-accepted replacement | 1024 x 1536 | `9B54F614F10BB6D3E9ED161ADD06F3B0C4D4336D29421CA3B3FB8452300A1514` |
| `empty-light.png` | Admitted empty, light | 1024 x 1536 | `267FF120FF7D604E3FF498C839A5619FB0A0C8D9D767A334C206DDF6097CD752` |
| `empty-dark.png` | Admitted empty, dark | 1024 x 1536 | `65EB8BF736563D556AFF9368A960178112A9B4766A7CAE095222FB00FD69B243` |
| `permission-light.png` | Permission denied/current session, light | 1024 x 1536 | `2E02F39BCE652275271B9BEBF73549150B64425022489320B7B0F21A16C5AF14` |
| `permission-dark.png` | Permission denied/current session, dark | 1024 x 1536 | `B8D612146D7048647812EB34596529E949B6DF455CCF7C12293D74B92CD4D8A2` |
| `unavailable-light.png` | Temporary unavailability and recovery, light | 1024 x 1536 | `B2E6F4CDE9DBF84ACF619E0F20C890DC0676F0150461A30204277FE019721B91` |
| `unavailable-dark.png` | Temporary unavailability and recovery, dark | 1024 x 1536 | `93599558D1B4EF4B83F573F92737F4C9B4BECE1C86073467AE1896F6976DF323` |
| `no-published-slate-light.png` | No published Slate, light | 1024 x 1536 | `7FC747A8CCFEC49FD86DEF435CF213D2FB5D10BE4B175DF8E797022ADB30C92B` |
| `no-published-slate-dark.png` | No published Slate, dark | 1024 x 1536 | `DF1CD0C3EB4E08BEEB2A7F145B6E8E21C842CF188F206285FF9464EE98D0F145` |

The rejected dark loading draft with SHA-256
`3983BEE6A69F09D0AD38FB85C1D0A7FAB5CCCB133867DEA0A469D62570E373C3`
is intentionally absent.

## Exact state copy

### Not connected

> Your Build Your Future workspace is not connected yet.
>
> Board items, editing, and future tools will arrive in later slices.
> Nothing has been created or changed.

### Loading

> Loading your Build Your Future workspace...
>
> We're checking the current workspace state.
> Nothing has been created or changed.

The future implementation may use the typographically correct ellipsis and
curly apostrophe while preserving the wording and meaning.

### Empty

> No supported work is connected here yet.
>
> The workspace is available, but there is no supported work to show.
> You can return to Workshop. Nothing has been created or changed.

### Permission denied

> This protected workspace isn't available to your current session.
>
> Nothing private has been shown.
> You can return to Workshop. Nothing has been created or changed.

### Unavailable

> Build Your Future is temporarily unavailable.
>
> We couldn't load the protected workspace right now.
> Try again or return to Workshop. Nothing has been created or changed.

### No published Slate

> No published Slate yet

This replaces the published-Slate link only when the server authoritatively
reports that no published Slate exists. It does not change the Board state.

## Boundaries

- Relationship curves are absent in every file in this folder. They remain
  selected-item or explicit show-connections state only in later slices.
- Unauthenticated behavior remains the existing protected-route sign-in
  redirect; the private shell must not be rendered before authentication.
- Reduced-motion requires no alternate raster because Slice 1 needs no motion
  to communicate state. Runtime behavior still requires verification.
- Long/localized content, browser text scaling, screen-reader order, real focus
  behavior, and exact contrast remain implementation acceptance evidence.
- None of these files authorizes Board data, Board persistence, editing,
  experiments, Ask Slate, grounded practice, publishing, a rename, Community
  pulse, or public-page alignment.

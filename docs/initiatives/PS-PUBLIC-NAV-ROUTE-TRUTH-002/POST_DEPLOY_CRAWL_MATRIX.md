# Post-deploy navigation crawl matrix

Deployment is outside this package. Run this matrix only after a separately
authorized deployment and bind every result to the deployed release identity.
Do not submit forms, create content, call providers, or infer authenticated
member proof from signed-out redirects.

| Audience/configuration | Routes and representations | Required result |
|---|---|---|
| Signed out, legacy Opportunity | `/`, `/petec/resume`, `/petec/my-story`, desktop header, room switcher, Menu, no-script navigation, public search | Pete's Slate, available Community, Interview Studio, and Opportunity Slate are consistent. My Story and Résumé remain in profile tabs. Capture, Slate Board, and Workshop are absent from navigation. |
| Signed out, V2 Opportunity | `/`, `/petec/resume`, `/opportunity-slate` | Public navigation advertises only the enabled registered V2 route. Opening its private room follows the expected sign-in gate without exposing member state. |
| Authenticated member | `/app`, account menu, Menu, phone bar, member search | `/app` is a neutral private starting point, never Pete's Profile. Cards are available Opportunity Slate, Interview Studio, Community, and Settings. Sign out remains a POST action. |
| Feature interactions | Community off/on; registered Opportunity implementation off/on; Workshop off/on | Each navigation destination follows its actual registered endpoint and controlling flag. Workshop remains unpromoted even when its compatible runtime is enabled. |
| Safe exact returns | `/app`, `/app/settings`, `/app/capture`, available Workshop roots, `/the-slate`, policy/deleted roots, Interview root/history, V2 Opportunity root | GET and HEAD resolve to the approved endpoint. A signed-out round trip returns only to the declared canonical landing. |
| Declared queries | Interview `mode=me`, `mode=ai`, available `mode=video`; V2 Opportunity `step=replace` | Values round-trip in canonical encoded form only when the related mode and route are available. Other keys, values, duplicates, and fragments fall back safely. |
| Hostile and unknown returns | External and protocol-relative URLs, controls, overlength input, literal/encoded/double-encoded separators and dots, auth/provider paths, unknown children, wrong methods | Every value reaches the validated default or `/app`; none is reflected into a provider redirect. |
| Opaque/action returns | Export job, capture draft/media, Workshop item/action, Community post/contribution/action, V2 Opportunity source/action | Each recognized route collapses to its declared parent with no opaque key in HTML, redirect, logs, or analytics. Unknown objects fall back to `/app`. |
| Retained compatibility | Direct `/app/capture`, enabled `/app/workshop`, `/petec/slate-board`, `/the-slate` | Existing routes keep their current access/privacy behavior. Their absence from navigation does not delete content or claim retirement. Feed remains canonical at `/the-slate`. |
| Held previews | `/career-search`, `/my-network`, `/explore-profiles`, `/for-recruiters`, `/peerslate` referring card, sitemap | Handler status/content, shared preview template/card, and exactly one sitemap entry per preview match the pre-package behavior. |
| Privacy lifecycle | Sign out/in, incomplete principal, identity storage unavailable, browser back/forward cache | Private prefixes remain `private, no-store`, no member data appears signed out, failure pages do not loop to the provider, and back navigation cannot reveal stale private HTML. |
| Responsive/accessibility | 320, 390, 768, 1280 CSS pixels; keyboard; reduced motion; JavaScript disabled; genuine 200% and 400% zoom | Navigation reflows without scoped overflow, controls remain operable and named, Escape restores focus, no-script destinations remain usable, and genuine zoom is recorded separately from viewport emulation. |

Record the deployed source SHA, pipeline/run identifier, release identity,
timestamp, exact configuration, redirect chain, and any limitation beside the
result. A local synthetic pass or screenshot does not satisfy this production
crawl.

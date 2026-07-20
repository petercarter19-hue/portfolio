# State matrix

| State | Intended visual behavior | Truth and recovery rule | Export |
|---|---|---|---|
| Current empty Home | Capture dominant; Review and Recent state exactly what is empty; dormant future capabilities remain polished | No fabricated record, count, activity, person, result, or media | 01, 13 |
| Future populated maximum | Same composition with persistent global and item-level fixture labels | Exactly 9 generic objects; not member data; not production | 02, 04, 06, 19 |
| Loading | Stable Owner Home and Capture-region structure; restrained inert placeholders only for live categories | No previous payload shown as current; no fake text/counts | 12 |
| Partial failure | Only Recent changes to named failure; Review, dormant slots, and Next remain intelligible | Retry repeats the same bounded request; no scope broadening | 14 |
| Complete failure | Owner Home heading remains; independently safe Capture remains; clear Retry and safe return | No raw stack/error ID and no cached-private fallback | 15 |
| Stale concurrency | Explicit `Stale`; affected action disabled; Refresh visibly focused | Re-authorize before retrieval; never silently overwrite | 16 |
| Restricted / not found | Neutral unavailable heading; no title, media, count, timestamp, source, or reason | Non-enumerating response and safe return | 17 |
| Retry succeeds | Updated category and one concise completion result | Move focus only if invoking control disappears; announce once | 18 left |
| Retry fails | Context retained; repeatable Retry and safe return | No duplicate appended errors or broader fallback | 18 right |
| Coming later | Full intended silhouette with feature name and complete **Coming later** label | No route, request, form value, fixture result, person, count, notification, output, or success state | All current screens |
| Private / unpublished | Explicit owner/private context; fixture review rows use `Private draft` | Previewing or managing never implies publication | 02, 04, 06 |
| Reduced motion | Static atmosphere and status; no parallax, carousel, reordering, shimmer dependency, or delayed removal | Runtime media query remains required | 11 |
| High contrast | White text/borders and visible focus on black; all state meanings in text | Runtime forced-colors mapping remains required | 10 |
| Viewer empty / unpublished | Distinguishes an authorized projection with zero eligible items from no published projection | Neither treatment implies that private content exists | 22 |
| Revoked / access changed | Sensitive content is absent; explicit access-changed heading receives intended focus before safe return | Clear DOM, client state, media, and caches immediately; no stale fallback | 22 |
| Deleted | Minimal lifecycle tombstone only | No reconstructed title, body, media, timestamp, or prior action | 22 |
| Session expired | Protected data absent; safe sign-in return | No private payload in URL, title, analytics, or browser history | 22 |
| Slow response / timeout | Same bounded request; no duplicate request; Retry and safe navigation | Never broaden authorization scope or duplicate a mutation | 22 |
| Unknown / direct-object | Neutral non-enumerating unavailable response | Fail closed without confirming that a private subject or item exists | 22 |
| Orientation change | Same semantic order in a standalone 844 px landscape-width reflow | Runtime state, data, and focus persistence remain required tests | 23 |

These exports are static visual requirements, not proof that lifecycle behavior, authorization, DOM clearing, cache/media invalidation, focus movement, or orientation persistence is implemented.

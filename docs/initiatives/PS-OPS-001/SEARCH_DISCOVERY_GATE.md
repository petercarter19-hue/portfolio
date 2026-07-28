# PS-OPS-SEARCH-QUIET-001 and Search Discovery Gate

## Current owner decision

Pete directed PeerSlate on 2026-07-28 to remain accessible through direct
links while reducing accidental discovery through search engines as much as
practical. He also directed that reopening search discovery must be a future
gate rather than an informal cleanup.

The current state is therefore **Quiet Preview**:

- direct-link visitors may continue to use intentional public routes;
- signed-in and private-member authorization boundaries do not change;
- shared public HTML carries
  `noindex, nofollow, noarchive, noimageindex`;
- search visibility is not privacy, authentication, or an invitation-only
  boundary; and
- Pete's public projection does not make another member public.

## Current bounded implementation

`templates/base.html` owns the fail-closed HTML directive for the shared public
shell. Focused route tests prove that the homepage, Experience, My Story,
Living Resume, Interview Studio, and Why PeerSlate remain reachable through
direct links while carrying the quiet-preview directive.

This slice deliberately does not edit `app.py`. A separate active Overview
writer owns that file at implementation time. PeerSlate's one-writer rule
prohibits a concurrent edit even when the intended changes are in different
functions.

Because of that reservation, the current dynamic `robots.txt` remains
crawlable and the current sitemap remains available. Crawlability is required
for compliant search engines to read and act on the HTML `noindex` directive,
but the sitemap continues to advertise routes until the response-level
follow-up below can safely land.

## Response-level quiet-preview follow-up

After the active `app.py` writer commits, pushes, and explicitly relinquishes
that file, a focused continuation shall:

1. add a site-wide `X-Robots-Tag` quiet-preview response header, including
   non-HTML responses where appropriate;
2. stop advertising public routes through the sitemap while Quiet Preview is
   active;
3. keep public HTML crawlable so search engines can observe `noindex`;
4. preserve crawler exclusions for `/app`, `/api/`, and `/owner`;
5. add tests for hidden and future-discoverable modes;
6. verify direct-link access to the intended public showcase; and
7. use Search Console removal/recrawl tools for URLs already indexed.

No one may claim those response-level or Search Console actions are complete
until exact implementation and production evidence exists.

## Future Search Discovery Gate

Search discovery remains locked until Pete explicitly opens this gate. The gate
is a specialization of `PS-OPS-001` Gate Launch and must record:

1. **Owner decision:** Pete approves the exact searchable audience and launch
   date.
2. **Public route inventory:** every indexable route has an intentional purpose,
   owner, current content, canonical URL, title, description, social metadata,
   and truthful status.
3. **Private-by-default proof:** unpublished member profiles and all private
   Journal, Studio, source, draft, and owner routes remain authorization-first
   and absent from public discovery.
4. **Public showcase boundary:** Pete's public Slate, My Story, Ask Pete AI,
   Interview Studio, Workshop preview, and Build Your Future preview expose
   only their separately approved public or disposable-sandbox contracts.
5. **Operational readiness:** applicable legal/privacy, accessibility,
   responsive, performance, abuse/rate-limit, support, incident, and owner
   disable evidence is accepted for the exact release.
6. **Search configuration:** the quiet-preview meta/header is removed or
   switched to discoverable mode, `robots.txt` is reconciled, and only the
   approved canonical routes enter the sitemap.
7. **Search ownership:** Search Console ownership is verified, the curated
   sitemap is submitted, obsolete URLs are removed or redirected, and indexed
   results are inspected.
8. **Production verification:** the exact deployed release is checked for
   index/noindex headers and metadata across the full approved route inventory.
9. **Rollback:** one named operator can return the site to Quiet Preview without
   changing direct-link access or private-member authorization.

Passing this gate changes search discoverability only. It does not publish a
member, broaden an audience, enable a private feature, or approve public beta
by itself.

# Routes, Shell, and Compatibility

## Canonical HTML routes

```text
/<profile_slug>                         Home
/<profile_slug>/posts
/<profile_slug>/posts/<projection_key>
/<profile_slug>/projects
/<profile_slug>/projects/<projection_key>
/<profile_slug>/media
/<profile_slug>/media/albums/<projection_key>
/<profile_slug>/voice
/<profile_slug>/voice/<projection_key>
/<profile_slug>/about
/<profile_slug>/resume                 preserved
/<profile_slug>/my-story               preserved

/app/profile                           authenticated owner alias
/app/profile/preview/public            exact anonymous Public preview
/app/profile/preview/connections       exact eligible Connections preview
```

Product-reserved route names cannot be registered as profile slugs. Opaque
projection keys, not sequential database IDs or private source IDs, appear in
selected-object routes.

## Viewer resolution on canonical routes

- Anonymous `/<slug>` resolves Public.
- An authenticated active Connection resolves Connections.
- The subject owner resolves Owner working mode.
- A signed-in unrelated member resolves only Public, through the Public reader.
- A query string, browser setting, hidden input, or JavaScript state never
  widens audience.
- Exact Public preview is a separate owner-authenticated route whose content
  comes from the same anonymous Public query and serializer as the real page.

Owner mode does not place every private source in the main Profile body. It
adds contextual commands and owner-safe status around the current body; private
source browsing and drafts appear only after an explicit Add or Manage action.

## Authenticated ingress

`/app` remains the stable entry address and compatibility router. Before
Profile enablement, it keeps current behavior. At approved cutover:

1. direct sign-in lands at `/app`;
2. `/app` resolves identity and redirects to `/app/profile`;
3. `/app/profile` resolves the owner's active slug and redirects to
   `/<slug>` in Owner mode; and
4. a valid protected deep link always wins over the default.

Safe return handling preserves normalized path plus query, never fragments or
private content. Expired POST requests are not replayed automatically.

## Shell contract

The first release reuses the current global PeerSlate header. Profile defines
one local context row only:

- destinations on the left: Home, Posts, Projects, Media, Voice, About;
- Profile search when that real dependency is enabled;
- owner actions on the right in Owner mode: Add something, Manage, View as
  public.

There is no separate permanent owner-control bar above or below this row. At
mobile widths, destinations and owner actions move into labeled sheets without
stacking several nav tiers above the dominant object.

The Profile identity/current-chapter region is content, not another navigation
bar. Résumé, My Story, and Ask `[Name]` are quiet deeper paths within it.

The visual package's shared-shell board governs Profile's local interface and
viewer/owner differences. It does not decide the sitewide future prominence of
Capture or Slate, mobile app navigation, or a complete global shell redesign.
Those remain a separate shared-shell program decision.

## Compatibility while dark

With `PEERSLATE_PROFILE_EXPERIENCE_ENABLED=false`:

- `/petec` continues to redirect to `/petec/resume`;
- `/petec/resume`, `/petec/my-story`, Ask Pete, and current metadata remain
  unchanged;
- `/petec/projects`, `/petec/work`, `/projects`, and `/work` keep their current
  résumé-experience redirects;
- `/petec/about` keeps the current page;
- new Profile HTML and APIs return neutral unavailable/404 behavior;
- no new sitemap, canonical, Open Graph, index, or navigation claim appears.

## Approved cutover

Only after dark verification and Pete's explicit enablement decision:

- `/<slug>` becomes Profile Home for members with a current Public publication;
- `/petec` stops redirecting and becomes Pete's Profile Home;
- `/<slug>/projects` becomes Profile Projects when real projections exist;
- `/<slug>/work` redirects to `/<slug>/projects`;
- `/petec/about` becomes Profile About after its content is explicitly
  imported/re-authored and published;
- `/projects` remains a product-level reserved route, not a Pete-specific alias;
- Résumé and My Story keep their canonical URLs;
- retired slugs resolve through an append-only slug history and canonical
  redirect; never-public or unavailable slugs return neutral 404.

## Metadata and indexing

Canonical URL, title, description, Open Graph image, and structured data are
derived from the exact current Public publication only. Connections and Owner
views are `noindex` and `no-store`. An unpublished destination is absent from
sitemaps and public search indexes. Withdrawal invalidates Profile search and
public metadata in the same release workflow.

Profile slugs are normalized and reserved across both current and historical
ownership. A slug previously held by one Profile is never reassigned to
another Profile. A historical slug may redirect only while it still belongs to
the same active Profile and that Profile has a current Public publication;
otherwise it returns the neutral unavailable response without revealing
identity, account, publication, or relationship state.

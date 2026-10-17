# Round-5 site shell, home page and theme: acceptance and execution record

**Goal:** build exactly Pete's approved round-5 designs, nothing added: the round-5 home page at `/`; the round-5 top bar and the Cairn icons on every page; and the owner resume page's existing green and beige theme site-wide from one shared token file.

**Authority:** Pete, 2026-10-13, on round 5: "That's it. Update this page. That's the one." Owner ref `role:owner/pete-chat-2026-10-13/claude-manager-16023c0e/home-page-round5-approved`. Same thread: the favicon ("make sure the logo… on the tabs changes as well"; a green square with white stones), the header on every page ("all of the pages… just in Coming soon, like you did in the homepage"), the site-wide theme (2026-10-14: "every other page has that same green and theme that the resume page has") and the footer "A" (2026-10-14: no Privacy or Terms links until those pages exist). Locked designs: `plans/home-screen-2026-10-13/round5/` (`mockups/concept-2.html`, `screens/`) and the theme tokens in `static/css/resume-page.css` on main. The shared shell files were released by PS-PUBLIC-TRUST-PAGES-001 (PR 1397, `2b743509`). Writer `agent:claude/2026-10-15/site-shell` (Claude PC, Opus 5.5) for the Claude PC site manager `session:16023c0e-7189-420e-8a4d-11f8012a9713`. Protected path; Codex gives the independent exact-SHA review. Production, schema, configuration, enablement and paid AI calls are withheld.

## Design

- **Home page:** `templates/homepage.html` extends `base.html` and renders the round-5 hero (cream Cairn, headline, lede, gold "See Pete's resume" and the "See Pete's story" link, invitation line), then the five-card fan as two `<picture>`s cropped from the locked mock-up (WebP 1x/2x with a PNG fallback, a phone variant, a description of each layout's cards). The off-layout picture resolves to a 1x1 data URI, so a phone never downloads the desktop fan. The body keeps `home-v3-page` for the deployment smoke check. The footer is the round-5 minimal footer (`partials/public_footer.html`).
- **Top bar:** one partial, `partials/site_header.html`, included by `base.html`. Its open links come from one list set in `base.html` from the server's verified destination groups, so the bar, the Menu sheet and the no-script list cannot disagree:
  - not signed in: My Resume and My Story (`profile_destinations`, Pete's public demo pages; the server already empties them on another member's public page);
  - signed in: the member's own My Resume (`account_destinations` `member_resume`, present only while that route is available; otherwise it is Soon too). My Story is not a member feature yet, so it is Soon.
  - Every other name is plain-text Soon: Interview Studio, My PeerSlate, Community, Opportunity Slate, My Opportunities. Existing auth controls (Sign in, the account menu) and the phone Menu stay.
  - Removed from the bar because round 5 has none: the header search field, the medium-width room switcher and the signed-in room name beside the logo. The search index JSON stays in the page, inert without a field.
  - `static/css/site-header.css` holds the mock-up's values, scoped to `#site-header` so legacy header rules cannot leak in; it loads last.
- **Icons:** `partials/site_icons.html` links the Cairn set in `static/images/site-icons/` (ico, svg, 16, 32, 192, 512, 180 apple-touch) from `base.html`, `control_room.html` and `feed_living_stream_states.html`. The old icon files stay for pages that still name them. No manifest exists, so none is added.
- **Theme:** `static/css/peerslate-theme.css` holds exactly the resume page's existing colour and backdrop values as `--ps-*` tokens and loads first. The shared `editorial-glass.css` layer (every page except `/` and `/experience`) applies them: the 6a `#3f6a51` backdrop with faint Cairn stones, the beige frame the content sits in, beige cards (`#faf6ec`, edges `#e3d7c1`, current item `#e8dfc9`), green plain links, gold Soft Sheen primary buttons, a light footer on the green. Light only. The owner resume page keeps painting its own theme. The Guide window is untouched. `resume-page.css` is not edited (named Lane D follow-up: point its `--rp-*` colours at the shared tokens).
- **Footer links:** Privacy and Terms render only when `public_policy_links_available` is true. Nothing sets it today (interface request to the policy routes' owner, SM3), so the links stay hidden and no missing endpoint can raise.

```package-acceptance-json
{
  "schema_version": 1,
  "package": "PS-SITE-SHELL-ROUND5-001",
  "plan_sha": "90d83d3148994f7c6b3c6d6da18df38b8270e215",
  "baseline": [
    {
      "command": "python -B -m unittest tests.test_public_nav_route_truth tests.test_homepage_scenes tests.test_shared_shell_convergence tests.test_navigation tests.test_auth tests.test_resume_access_nav tests.test_search_visibility tests.test_workshop_checkpoint tests.test_dark_theme_availability tests.test_http_edge_security tests.test_people_interests_feed tests.test_interview_recovery_mobile_nav_browser tests.test_site_rules -q",
      "exit_code": 0,
      "observation": "Pre-change at 6702b10d (accepted main with this claim and Lane D's D2): 303 tests PASS in 17.7s with the placeholder key and fictional members. The home page is the MVP1 minimal body (one aurora picture, 'A considered beginning'). Every page has the old white header: the metallic logo image, My Resume and Interview AI (signed out), a search field, a room switcher, 'Sign In', and peerslate-favicon.png. Pages use the blue-white editorial background. No shared theme token file exists."
    }
  ],
  "criteria": [
    {
      "id": "home_round5",
      "expected": "/ renders Pete's round-5 home page and nothing else: the cream Cairn, 'Your Work. Your Story. Your Future.', 'A portfolio that tells your story and answers for you.', the gold 'See Pete's resume' button to /petec/resume and the 'See Pete's story' link to /petec/my-story as the only two actions, the invitation line, the five-card fan as two pictures (WebP 1x/2x with a PNG fallback, a phone variant, a description of each layout's cards) and the minimal footer (Cairn and '© 2026 PeerSlate'). The title and the home-v3-page smoke marker are kept. At 1440, 1280, 1024 and 390 it reads the same as the round-5 screens.",
      "verification": "New tests in tests/test_site_shell_round5.py and the rewritten tests/test_homepage_scenes.py, RED at the base and GREEN at the candidate; screenshots next to the round-5 screens."
    },
    {
      "id": "header_everywhere",
      "expected": "Every base.html page renders the round-5 bar: the Cairn lockup linking home; signed out, My Resume (/petec/resume#resume-start) and My Story (/petec/my-story) then a quiet Soon tag with non-clickable Interview Studio, My PeerSlate, Community, Opportunity Slate and My Opportunities; signed in, only the member's own My Resume (/app/resume) when that route is available, with My Story and the rest under Soon and no /petec link; the existing Sign in or account menu; the phone Menu whose sheet and the no-script list repeat the bar exactly. There is no search field, room switcher or room title in the bar, and no horizontal scroll from 320 to 1440 px.",
      "verification": "New and updated route tests across the affected modules (bar, Menu, no-script, signed out and in, another member's page); browser checks at 320, 360, 375 and 390; screenshots of six other pages before and after."
    },
    {
      "id": "cairn_icons",
      "expected": "Every base.html page, control_room.html and feed_living_stream_states.html link the Cairn icon set (green square, white stones): favicon.ico, favicon.svg, 16, 32, 192, 512 and the 180 apple-touch icon, all content-versioned. The previous icon files stay in the repository.",
      "verification": "New tests read the rendered head and the image files (real PNG/ICO/WebP of the declared size)."
    },
    {
      "id": "shared_theme",
      "expected": "One new token file, static/css/peerslate-theme.css, holds exactly the resume page's existing colour and backdrop values, loads first on every base.html page, and is the only source the site-wide theme section reads. Every page except / and /experience shows the 6a #3f6a51 backdrop with faint Cairn stones, content in the beige frame, beige cards (#faf6ec, #e3d7c1, current #e8dfc9), green plain links and gold Soft Sheen primary buttons; light only; resume-page.css and the Guide's CSS are unchanged.",
      "verification": "New token-parity and theme-scope tests; screenshots before and after."
    },
    {
      "id": "policy_footer_links",
      "expected": "The round-5 footer shows Privacy and Terms only when public_policy_links_available is true, and with the flag absent it renders without touching a missing endpoint. Today no such route exists, so the links are hidden (Pete's 'A').",
      "verification": "New tests render the footer with the flag true (routes registered), false and absent."
    },
    {
      "id": "regression_and_routes",
      "expected": "No regression: the affected suites pass; the strict MVP1 browser runner passes normally and twice concurrently; changed browser modules skip cleanly without Playwright; a whole no-Playwright discover has the same failure set as the base; /, /petec/resume, /my-story, /petec/my-story and /app/resume answer as before, signed in and out.",
      "verification": "Recorded runs at the candidate and at the base."
    },
    {
      "id": "review_and_delivery",
      "expected": "Codex's independent exact-SHA review passes with no open Critical, High or Medium finding, and Pete's screenshot OK is recorded before merge. Merge only; no deployment.",
      "verification": "Review receipt and coordination record."
    }
  ],
  "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
  "checks": [
    {
      "criterion_id": "home_round5",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + tests.test_site_shell_round5.HomePageRound5Tests + tests.test_homepage_scenes",
      "observed": "The round-5 home page renders exactly the approved hero copy and its two actions, the fan as two described pictures with webp and png fallback, the minimal footer, the page title and the deployment smoke marker. The independent reviewer measured the header at 0.0% pixels different from the approved mock-up at 1440, 1280, 1024 and 390, the rest differing only by anti-aliasing on the fan picture's edges and the footer's absent Privacy and Terms (Pete's A); no home-page file changed after that measurement."
    },
    {
      "criterion_id": "header_everywhere",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + tests.test_site_shell_round5.TopBarEverywhereTests + tests.test_site_shell_round5.MenuEachDestinationOnceTests + tests.test_site_shell_round5.SignedInPhoneBrowserTests + tests.test_site_shell_round5.PhoneHeaderReviewFixBrowserTests + tests.test_navigation + tests.test_public_nav_route_truth + tests.test_shared_shell_convergence",
      "observed": "Every page renders the round-5 bar from one partial: signed out My Resume and My Story then the quiet Soon names, signed in the member's own My Resume with everything else Soon, no bar on another member's page; the phone Menu repeats the bar exactly with each destination once and no sideways scroll at 320 and 390, signed in and out; the signed-in phone bottom bar is retired. The independent reviewer re-checked the bar, Menu and account menu on the earlier candidate and found every word passing."
    },
    {
      "criterion_id": "cairn_icons",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + tests.test_site_shell_round5.TopBarEverywhereTests.test_every_page_links_the_cairn_icons_and_the_shared_theme + tests.test_site_shell_round5.HomePageRound5Tests.test_fan_and_icon_files_are_real_images_of_the_declared_size",
      "observed": "Every base page and the two standalone templates list favicon.ico first and link the Cairn set; the image files are real PNG, ICO and WebP of the declared sizes; the independent reviewer fetched all seven icon files (200, right types)."
    },
    {
      "criterion_id": "shared_theme",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + tests.test_site_shell_round5.SharedThemeTokensTests + tests.test_site_shell_round5.WholeSiteThemeBrowserTests + tests.test_site_shell_round5.ResumeContactButtonInkSourceTests + tests.test_site_shell_round5.GreenEverywhereSourceTests",
      "observed": "One token file holds the resume page's values and nothing else redefines them; on 54 routes, signed out and in, at 1440 and 390, the document is the theme green with green page edges and no white or navy page fill; no navy, blue, teal or plain-white fill, border, pseudo-element layer or text remains inside the content (sections scrolled into view and the Credentials panel opened first); every visible word reads at 4.5:1 (3:1 large) against its real pixels, the Career Constellation's words included; every text box on every route reads when typed into, shows its placeholder at 4.5:1 and a visible focus change. Named exceptions carry their reasons in the tests, and the reviewer's mutants fail these tests."
    },
    {
      "criterion_id": "policy_footer_links",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + tests.test_site_shell_round5.SiteFooterPolicyLinksTests + tests.test_site_shell_round5.SiteFooterPolicyLinksBrowserTests + tests.test_site_shell_round5.PolicyFooterLinksTests",
      "observed": "The footer shows Privacy and Terms only while public_policy_links_available is true; with the flag absent or false it renders no link and never builds the endpoint; with it true both footers carry the same pair, reachable by keyboard and reflowing at 320 and 390. No production code sets the flag, so no link renders today (confirmed by the independent reviewer)."
    },
    {
      "criterion_id": "regression_and_routes",
      "result": "pass",
      "kind": "automated",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bee327e:Shared/handoffs/2026-10-17_claude-pc_to-claude-pc_REVIEW_PS-SITE-SHELL-ROUND5-001_e4cb4ff4.md + coordination:625a8a5:Shared/handoffs/2026-10-17_claude-pc_to-claude-manager_PS-SITE-SHELL-ROUND5-001_review-sha-moves-14.md",
      "observed": "At the candidate: the 68 affected modules pass (2097 run, 4 skipped, 0 failures); the shell browser modules pass under load in two concurrent copies (134 run each, 0 skipped); the changed browser modules skip cleanly without Playwright (292 run, 141 skipped, 0 errors); the strict MVP1 runner passes normally and as a concurrent pair (210/210 and 210/210, 0 skipped); the whole no-Playwright discover against current main shows 12 errors and 13 failures, every one also failing on main, nothing new."
    },
    {
      "criterion_id": "review_and_delivery",
      "result": "pass",
      "kind": "manual",
      "candidate_sha": "e4cb4ff4ac51327b56b602b20a42e30de07b8fdf",
      "source_ref": "coordination:bdfb518:Shared/handoffs/2026-10-17_peter-approved_shell-screenshots-ok.md",
      "observed": "An independent read-only exact-SHA review of the candidate passed with no open Critical, High or Medium finding (a separate Claude reviewer, as arranged by the manager), and Pete's screenshot approval of the candidate is recorded before merge ('Fine with the rest' and 'That looks excellent. Thank you. All right, make all the changes and go.'). One exception stands: Pete does not accept the old resume layout as the end state; it stays recoloured in its current layout only until PS-RESUME-PAGE-LIVE-001 replaces it with the approved member design. This is a merge only, with no deployment.",
      "provenance": {
        "observer_ref": "role:owner/pete",
        "captured_at": "2026-10-17T13:24:00-05:00",
        "source_ref": "coordination:bdfb518:Shared/handoffs/2026-10-17_peter-approved_shell-screenshots-ok.md"
      }
    }
  ]
}
```

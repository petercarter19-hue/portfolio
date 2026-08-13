import json
import re
import unittest
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

from app import app


class PlatformNavigationParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_platform_nav = False
        self.current_link = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        classes = attributes.get('class', '').split()

        if tag == 'nav' and 'platform-nav' in classes:
            self.in_platform_nav = True
        elif self.in_platform_nav and tag == 'a':
            self.current_link = {'attributes': attributes, 'text': ''}

    def handle_data(self, data):
        if self.current_link is not None:
            self.current_link['text'] += data

    def handle_endtag(self, tag):
        if self.current_link is not None and tag == 'a':
            self.current_link['text'] = self.current_link['text'].strip()
            self.links.append(self.current_link)
            self.current_link = None
        elif self.in_platform_nav and tag == 'nav':
            self.in_platform_nav = False


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def parse_platform_links(self, path, base_url='http://localhost'):
        response = self.client.get(path, base_url=base_url)
        self.assertEqual(response.status_code, 200)
        parser = PlatformNavigationParser()
        parser.feed(response.get_data(as_text=True))
        return parser.links

    def search_records(self, path='/', base_url='http://localhost'):
        response = self.client.get(path, base_url=base_url)
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        match = re.search(
            r'<script id="nav-search-data" type="application/json">(.*?)</script>',
            html,
            re.DOTALL,
        )
        self.assertIsNotNone(match)
        return json.loads(match.group(1))

    def test_petes_slate_opens_the_canonical_resume_and_redundant_home_is_omitted(self):
        for path in ('/', '/petec/resume'):
            with self.subTest(path=path):
                links = self.parse_platform_links(path)
                links_by_text = {link['text']: link for link in links}

                self.assertNotIn('Atrium', links_by_text)
                self.assertEqual(
                    links_by_text["Pete's Slate"]['attributes']['href'],
                    '/petec/resume#overview',
                )
                self.assertNotIn('Home', links_by_text)

        homepage_links = {
            link['text']: link for link in self.parse_platform_links('/')
        }
        resume_links = {
            link['text']: link
            for link in self.parse_platform_links('/petec/resume')
        }
        self.assertNotIn(
            'aria-current',
            homepage_links["Pete's Slate"]['attributes'],
        )
        self.assertEqual(
            resume_links["Pete's Slate"]['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('Home', resume_links)

    def test_header_search_omits_retired_overview_and_projects_records(self):
        records = self.search_records()
        titles = [record['title'] for record in records]

        self.assertNotIn('Overview', titles)
        self.assertNotIn('Projects', titles)
        self.assertIn('Résumé', titles)
        resume = next(record for record in records if record['title'] == 'Résumé')
        self.assertEqual(resume['href'], '/petec/resume#resume-start')
        for retired in (
            'Community · My Slate',
            'Community · Daily Slate',
            'Community · My Paths',
            'Feed · Pulse',
            'Feed Preview · Living Stream',
        ):
            self.assertNotIn(retired, titles)

    def test_global_product_names_and_links_use_the_new_information_architecture(self):
        links = {
            link['text']: link
            for link in self.parse_platform_links('/interview-studio')
        }
        self.assertEqual(links['Community']['attributes']['href'], '/the-slate')
        self.assertEqual(links['Interview Studio']['attributes']['href'], '/interview-studio')
        # v1.2 (PS-BRAND-NAV-001): About left the header; the footer link
        # 'Why PeerSlate' points at the same route instead.
        self.assertNotIn('About PeerSlate', links)
        self.assertEqual(
            links['Interview Studio']['attributes'].get('aria-current'),
            'page',
        )
        self.assertNotIn('The Slate', links)
        self.assertNotIn('Interview Me', links)
        self.assertNotIn('About', links)

        records = self.search_records('/interview-studio')
        records_by_title = {record['title']: record for record in records}
        # PS-COMMUNITY-AUTH-WALL-001: the search entry is simply "Community"
        # and is honest about its members-only audience.
        self.assertEqual(records_by_title['Community']['href'], '/the-slate')
        self.assertEqual(
            records_by_title['Community']['sub'],
            'Visible to signed-in PeerSlate members',
        )
        self.assertNotIn('Community Feed', records_by_title)
        self.assertEqual(records_by_title['Interview Studio']['href'], '/interview-studio')
        self.assertNotIn('The Slate', records_by_title)

    def test_resume_subheader_ai_field_replaces_the_retired_overview_field(self):
        resume = self.client.get('/petec/resume', base_url='http://localhost')

        self.assertEqual(resume.status_code, 200)
        self.assertIn(b'data-resume-subheader-ask', resume.data)
        self.assertIn(b'id="subheader-ai-input"', resume.data)
        self.assertNotIn(b'data-overview-subheader-ask', resume.data)
        self.assertNotIn(b'id="overview-subheader-ai-input"', resume.data)

    def test_community_routes_do_not_inherit_petes_profile_subheader(self):
        # PS-COMMUNITY-AUTH-WALL-001: the legacy subviews forward to the one
        # real Community in every flag state, and Community itself is
        # members-only — flag off is a neutral 404, signed out goes through
        # sign-in. None of these responses carries Pete's profile subheader.
        original_flag = app.config.get('PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED')
        try:
            for flag in (False, True):
                app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = flag
                for path in (
                    '/the-slate/my-slate',
                    '/the-slate/daily',
                    '/the-slate/pulse',
                    '/the-slate/break',
                ):
                    with self.subTest(path=path, flag=flag):
                        response = self.client.get(path, base_url='http://localhost')
                        self.assertEqual(response.status_code, 302)
                        self.assertTrue(
                            response.headers['Location'].endswith('/the-slate')
                        )
                        self.assertNotIn(b'class="profile-tabs', response.data)

            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = False
            flag_off = self.client.get('/the-slate', base_url='http://localhost')
            self.assertEqual(flag_off.status_code, 404)
            self.assertNotIn(b'class="profile-tabs', flag_off.data)
            self.assertNotIn(b'id="chat-toggle"', flag_off.data)

            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = True
            signed_out = self.client.get('/the-slate', base_url='http://localhost')
            self.assertEqual(signed_out.status_code, 302)
            self.assertEqual(
                signed_out.headers['Location'],
                '/auth/sign-in?return_to=/the-slate',
            )
        finally:
            app.config['PEERSLATE_COMMUNITY_PUBLIC_PILOT_ENABLED'] = original_flag

        homepage = self.client.get('/', base_url='http://localhost')
        self.assertNotIn(b'the-slate-page', homepage.data)

    def test_public_mobile_menu_has_one_complete_global_destination_set(self):
        response = self.client.get('/interview-studio', base_url='http://localhost')
        html = response.get_data(as_text=True)

        self.assertIn('data-platform-menu-toggle', html)
        self.assertIn('id="platform-mobile-menu"', html)
        menu = html.split('id="platform-mobile-menu"', 1)[1].split('</nav>', 1)[0]
        for label in ("Pete's Slate", 'Community', 'Interview Studio'):
            self.assertEqual(menu.count(f'>{label}</a>'), 1)
        # PS-SHELL-001: the sheet no longer carries its own search field. The
        # header field is present at every width, so a second one here meant
        # two visible inputs with the same accessible name whenever the sheet
        # was open.
        self.assertNotIn('id="nav-search-input-mobile"', menu)
        self.assertEqual(html.count('class="nav-search__input"'), 1)

    def test_member_specific_ai_is_scoped_to_petes_public_slate(self):
        for path in (
            '/',
            '/the-slate',
            '/interview-studio',
            '/peerslate',
            '/experience',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertNotIn(b'id="chat-toggle"', response.data)
                self.assertNotIn(b'class="profile-tabs', response.data)

        for path in (
            '/petec/resume',
            '/petec/my-story',
            '/petec/slate-board',
        ):
            with self.subTest(path=path):
                response = self.client.get(path, base_url='http://localhost')
                self.assertIn(b'id="chat-toggle"', response.data)
                self.assertIn(b'class="profile-tabs', response.data)

    def test_private_owner_surfaces_do_not_inherit_petes_public_profile_tabs(self):
        """Pete's public tab strip is fixture content; a member's private
        owner pages must not publish it above their own workspace.

        PS-PUBLIC-NAV-001 set the contract ("Pete's profile navigation
        renders only on Pete profile routes") but the base.html condition
        still admitted every `/app` path, so Capture, Settings and Moment
        review each rendered My Story / Work / Slate Board / Resume plus a
        second Ask Pete AI control. Corrected 2026-08-03 (site visual parity
        audit, finding 10). `/app` itself is excluded from this test on
        purpose: it is the deferred legacy owner workspace that
        PS-HOME-FRONTEND-001 replaces, and its flag-off render is byte-locked
        by tests/test_owner_home.py.
        """
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'navigation-test-owner'
        try:
            for path in ('/app/capture', '/app/settings'):
                with self.subTest(path=path):
                    response = self.client.get(path, base_url='http://localhost')
                    # 200 with a database, 503 on the honest unavailable
                    # render without one; both use this shared shell.
                    self.assertIn(response.status_code, (200, 503))
                    self.assertNotIn(b'class="profile-tabs', response.data)
                    self.assertNotIn(b'profile-tabs__ask-btn', response.data)

            # The legacy /app workspace is deliberately unchanged.
            legacy = self.client.get('/app', base_url='http://localhost')
            self.assertEqual(legacy.status_code, 200)
            self.assertIn(b'class="profile-tabs', legacy.data)
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

    def test_public_search_is_navigation_only_without_an_ai_fallback(self):
        source = Path('static/js/public-site-search.js').read_text(encoding='utf-8')
        self.assertIn('No matching public destination', source)
        self.assertNotIn('Ask Pete', source)
        self.assertNotIn('data-ask-url', self.client.get('/').get_data(as_text=True))

    def test_opportunity_slate_link_sits_next_to_workshop_in_both_menus(self):
        """PS-OPPORTUNITY-SLATE-001 leg 7 (Pete's 2026-08-05 order): the link
        is unconditional, unlike Workshop's flag-gated entry beside it."""
        homepage_links = {
            link['text']: link for link in self.parse_platform_links('/')
        }
        self.assertIn('Opportunity Slate', homepage_links)
        self.assertEqual(
            homepage_links['Opportunity Slate']['attributes']['href'],
            '/opportunity-slate',
        )
        self.assertNotIn(
            'aria-current', homepage_links['Opportunity Slate']['attributes']
        )

        mobile_menu = self.client.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        menu = mobile_menu.split('id="platform-mobile-menu"', 1)[1].split(
            '</nav>', 1
        )[0]
        self.assertEqual(menu.count('>Opportunity Slate</a>'), 1)

    def test_opportunity_slate_link_shows_aria_current_on_its_own_room(self):
        original_flag = app.config.get('PEERSLATE_OPPORTUNITY_SLATE_ENABLED')
        app.config['PEERSLATE_OPPORTUNITY_SLATE_ENABLED'] = True
        try:
            links = {
                link['text']: link
                for link in self.parse_platform_links('/opportunity-slate')
            }
        finally:
            app.config['PEERSLATE_OPPORTUNITY_SLATE_ENABLED'] = original_flag
        self.assertIn('Opportunity Slate', links)
        self.assertEqual(
            links['Opportunity Slate']['attributes'].get('aria-current'), 'page'
        )

    def test_header_search_json_parses_with_opportunity_slate_in_both_workshop_states(self):
        """The Opportunity Slate record sits after Workshop's
        ``{% if workshop_nav_enabled %}...{% endif %}`` block, so the JSON
        must stay valid whether or not that flag is on."""
        original_workshop_flag = app.config.get('PEERSLATE_WORKSHOP_ENABLED')
        try:
            for workshop_enabled in (True, False):
                with self.subTest(workshop_nav_enabled=workshop_enabled):
                    app.config['PEERSLATE_WORKSHOP_ENABLED'] = workshop_enabled
                    records = self.search_records()
                    titles = [record['title'] for record in records]
                    self.assertIn('Opportunity Slate', titles)
                    self.assertEqual(
                        titles.count('Opportunity Slate'), 1
                    )
                    entry = next(
                        record
                        for record in records
                        if record['title'] == 'Opportunity Slate'
                    )
                    self.assertEqual(entry['href'], '/opportunity-slate')
                    self.assertEqual(
                        entry['sub'],
                        'See how your evidence lines up with a role',
                    )
                    self.assertIn('role', entry['keys'])
                    self.assertEqual('Workshop' in titles, workshop_enabled)
        finally:
            app.config['PEERSLATE_WORKSHOP_ENABLED'] = original_workshop_flag

    # ------------------------------------------------------------------
    # PS-SHELL-001 — the Editorial Top Bar
    # ------------------------------------------------------------------

    def signed_in_client(self):
        """A client whose SERVER render is authenticated, via the existing
        development-identity path. The shell's signed-in markup is
        server-derived, so it cannot be exercised any other way."""
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'shell-test-member'
        self.addCleanup(self._restore_config, originals)
        return app.test_client()

    def _restore_config(self, originals):
        for key, value in originals.items():
            if value is None:
                app.config.pop(key, None)
            else:
                app.config[key] = value

    def test_room_switcher_repeats_the_inline_destinations_and_adds_none(self):
        """The medium-width pill is an overflow mechanism, not a second
        information architecture: same hrefs and same active state as the
        inline row it replaces between 64.01rem and 73.75rem. Direction 2 adds
        a room icon and a one-line description per row, and each description
        is the wording the search index already uses for that room."""
        html = self.client.get(
            '/interview-studio', base_url='http://localhost'
        ).get_data(as_text=True)

        inline = html.split('class="platform-nav__links"', 1)[1].split(
            '</ul>', 1
        )[0]
        switcher = html.split('class="platform-roomswitcher__list"', 1)[1].split(
            '</ul>', 1
        )[0]

        inline_links = re.findall(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', inline)
        switcher_links = re.findall(
            r'<a href="([^"]+)"([^>]*)>.*?'
            r'__title">([^<]+)</span>'
            r'<span class="platform-roomswitcher__sub">([^<]+)</span>',
            switcher,
        )
        # The inline row's labels are literal template text; the switcher
        # renders them from one shared destination list, so Jinja escapes the
        # apostrophe. Compare the text, not the escaping.
        def unescape(value):
            return value.replace('&#39;', "'")

        self.assertEqual(
            [(href, 'aria-current' in rest, unescape(label))
             for href, rest, label in inline_links],
            [(href, 'aria-current' in rest, unescape(label))
             for href, rest, label, _ in switcher_links],
        )

        # Descriptions are the existing search-index wording, not a new claim.
        records = {r['title']: r['sub'] for r in self.search_records(
            '/interview-studio'
        )}
        for _, _, label, sub in switcher_links:
            if unescape(label) in records:
                with self.subTest(label=label):
                    self.assertEqual(unescape(sub), records[unescape(label)])

        # The pill names the room the viewer is in, and carries its mark.
        self.assertIn(
            '<span class="platform-roomswitcher__label">Interview Studio</span>',
            html,
        )
        self.assertEqual(
            switcher.count('class="platform-roomswitcher__mark"'),
            len(switcher_links),
        )
        # ...and says what it does, for a screen reader.
        self.assertIn('Browse destinations, current:', html)

    def test_room_switcher_label_falls_back_where_no_destination_is_active(self):
        homepage = self.client.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        # And it does not claim a current room that does not exist: the
        # released wording announced "current: Browse".
        self.assertIn(
            '<span class="platform-roomswitcher__label">Browse destinations</span>',
            homepage,
        )
        self.assertNotIn('Browse destinations, current:', homepage)
        # No room, so no phone room title either — the brand slot keeps the
        # logo rather than rendering empty.
        self.assertNotIn('platform-room-title', homepage)

    def test_the_logo_is_revealed_at_every_width_in_every_auth_state(self):
        """Owner direction, 2026-08-13: "logo should always be revealed ...
        It should always be revealed", naming 768-1024 signed in.

        Until this round a signed-in viewer inside one of the five
        destinations lost the mark entirely below 64rem, because the room
        title was drawn INSTEAD of it. The markup always carried the logo, so
        no template assertion could have caught that — a stylesheet rule
        removed it, and that rule is what this test guards. It also diverges
        from the approved boards, which draw the room name in place of the
        mark on a signed-in phone; the owner's written direction wins and the
        divergence is recorded in the package README.
        """
        stylesheet = Path('static/css/public-navigation.css').read_text(
            encoding='utf-8'
        )
        # Comments discuss the mark at length; only declarations count.
        declarations = re.sub(r'/\*.*?\*/', '', stylesheet, flags=re.S)
        blocks = re.findall(
            r'([^{}]*platform-brand__logo[^{}]*)\{([^{}]*)\}', declarations
        )
        self.assertTrue(blocks, 'expected the shell to style the brand mark')
        for selector, body in blocks:
            with self.subTest(selector=' '.join(selector.split())[-80:]):
                self.assertNotRegex(body, r'display\s*:\s*none')
                # Nor may it be hidden by any other route.
                self.assertNotRegex(body, r'visibility\s*:\s*hidden')
                self.assertNotRegex(body, r'\bcontent-visibility\s*:\s*hidden')

        # Where the row genuinely runs out of width it is the room title that
        # gives way, never the mark — and it gives way by never being shown
        # below 34rem rather than by being removed there. PS-SIGNIN-
        # EXPERIENCE-001 reserves the 34rem block for sign-out-scoped
        # compaction and forbids any rule there that removes a header control,
        # so the title is turned ON inside its own band and off nowhere.
        band = declarations.split(
            '@media (max-width: 64rem) and (min-width: 34.01rem)', 1
        )
        self.assertEqual(len(band), 2, 'the room title should own a band')
        self.assertRegex(
            band[1].split('}\n', 1)[0] + band[1].split('@media', 1)[0],
            r'platform-room-title\s*\{\s*display:\s*block',
        )
        crowded = declarations.split('@media (max-width: 34rem)', 1)
        self.assertEqual(len(crowded), 2, 'the 34rem block should still exist')
        self.assertNotIn(
            'platform-room-title', crowded[1].split('@media', 1)[0]
        )

        paths = ('/', '/interview-studio', '/opportunity-slate', '/petec/resume')
        # Anonymous first: signed_in_client() flips application config.
        anonymous = {
            path: self.client.get(path, base_url='http://localhost').get_data(
                as_text=True
            )
            for path in paths
        }
        signed_in = self.signed_in_client()
        for path in paths:
            with self.subTest(path=path):
                for html in (anonymous[path],
                             signed_in.get(
                                 path, base_url='http://localhost'
                             ).get_data(as_text=True)):
                    self.assertIn('class="platform-brand__logo"', html)
                    self.assertIn('images/peerslate-logo-header.png', html)

    def test_phone_header_names_the_room_beside_the_logo_when_signed_in(self):
        """The room title is additive, not a replacement. It renders only for
        a signed-in viewer inside one of the five destinations, is driven by
        data-ps-shell-room-title, which the SERVER writes and no script
        touches, and it sits beside a logo that is always there.
        """
        paths = ('/interview-studio', '/opportunity-slate', '/petec/resume')
        # Anonymous first: signed_in_client() flips application config, so a
        # client created before it would not stay anonymous.
        anonymous_renders = {
            path: self.client.get(path, base_url='http://localhost').get_data(
                as_text=True
            )
            for path in paths
        }

        signed_in = self.signed_in_client()
        for path, expected in zip(
            paths, ('Interview Studio', 'Opportunity Slate', "Pete's Slate")
        ):
            with self.subTest(path=path):
                html = signed_in.get(
                    path, base_url='http://localhost'
                ).get_data(as_text=True)
                # The label is a rendered value, so Jinja escapes the
                # apostrophe in "Pete's Slate".
                escaped = expected.replace("'", '&#39;')
                self.assertIn(' data-ps-shell-room-title>', html)
                self.assertIn(
                    '<span class="platform-room-title" '
                    f'data-platform-room-title>{escaped}</span>',
                    html,
                )

                # It is an addition to the brand row, not a substitution: the
                # mark is in the same render, immediately before it.
                self.assertLess(
                    html.index('class="platform-brand__logo"'),
                    html.index('class="platform-room-title"'),
                )

                anonymous = anonymous_renders[path]
                self.assertNotIn('data-ps-shell-room-title', anonymous)
                self.assertNotIn('platform-room-title', anonymous)
                self.assertIn('platform-brand__logo', anonymous)

        # A route that is not one of the five destinations names no room, and
        # shows the mark alone rather than an empty brand slot.
        homepage = signed_in.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        self.assertNotIn('data-ps-shell-room-title', homepage)
        self.assertIn('platform-brand__logo', homepage)

    def test_global_phone_bar_is_signed_in_only(self):
        """Both approved boards draw public phone navigation as hamburger,
        logo and Sign in with no bottom bar, which is also what production
        does today. A signed-out visitor must therefore keep the header Menu
        as their one navigation affordance — the bar must never render and
        take it away."""
        # Anonymous first: signed_in_client() flips application config.
        anonymous = self.client.get('/', base_url='http://localhost').get_data(
            as_text=True
        )
        self.assertNotIn('data-global-tabsource', anonymous)
        self.assertIn('data-platform-menu-toggle', anonymous)

        signed_in = self.signed_in_client().get(
            '/', base_url='http://localhost'
        ).get_data(as_text=True)
        self.assertIn('data-global-tabsource', signed_in)
        self.assertIn('data-platform-menu-toggle', signed_in)

    def test_global_phone_bar_source_offers_only_real_registered_routes(self):
        """Architecture section 5: the four-slot structure is a source list
        for the one existing bottom bar. Slot 1 keeps assumption A1's label
        because no per-member profile route is registered."""
        html = self.signed_in_client().get(
            '/interview-studio', base_url='http://localhost'
        ).get_data(as_text=True)
        source = html.split('data-global-tabsource', 1)[1].split('</ul>', 1)[0]

        self.assertIn(f'href="{"/petec/resume"}#overview" ', source)
        self.assertIn(">Pete's Slate</span>", source)
        self.assertNotIn('>Profile<', source)
        self.assertIn('href="/the-slate"', source)
        self.assertIn('>Community</span>', source)
        self.assertIn('href="/interview-studio"', source)
        # Short visible label, full accessible name (WCAG 2.2 SC 2.5.3).
        self.assertIn('aria-label="Interview Studio"', source)
        self.assertIn('>Interview</span>', source)
        # Three destinations plus the More slot, which is a button rather
        # than a destination and so carries no href.
        self.assertEqual(source.count('<li>'), 3)
        self.assertEqual(source.count('<li data-global-more>'), 1)
        self.assertEqual(source.count('href='), 3)
        # Every slot carries a server-rendered mark; nothing is built in
        # script from data.
        self.assertEqual(source.count('class="mobile-tabbar__mark"'), 4)
        self.assertEqual(source.count('class="mobile-tabbar__label"'), 4)

    def test_more_sheet_offers_settings_and_omits_a_help_route_that_does_not_exist(self):
        """The direction's More list names Help, but no Help route is
        registered anywhere in the application. Navigation gains no
        destination that lacks a real page, so Help is not offered."""
        html = self.client.get(
            '/interview-studio', base_url='http://localhost'
        ).get_data(as_text=True)
        menu = html.split('id="platform-mobile-menu"', 1)[1].split('</nav>', 1)[0]

        self.assertIn('>Settings</a>', menu)
        self.assertIn('href="/app/settings"', menu)
        self.assertNotIn('>Help<', menu)
        # Every one of the five destinations is still reachable from the sheet.
        for label in ("Pete's Slate", 'Community', 'Interview Studio',
                      'Opportunity Slate'):
            self.assertEqual(menu.count(f'>{label}</a>'), 1)

    def test_shell_offers_no_notification_or_add_control(self):
        """Neither has a real backing contract: no notification route, model
        or service exists, and /app/capture is owner-gated behind a
        fail-closed allowlist. The Add position is reserved in comment only,
        so a future member contract is an insertion, not a re-layout."""
        for path in ('/', '/interview-studio', '/petec/resume'):
            with self.subTest(path=path):
                html = self.client.get(
                    path, base_url='http://localhost'
                ).get_data(as_text=True)
                header = html.split('<header class="global-header">', 1)[1].split(
                    '</header>', 1
                )[0]
                for banned in ('notification', 'data-ps-notifications',
                               'data-ps-add', 'href="/app/capture"'):
                    self.assertNotIn(banned, header)

        # The reservation is a template marker, so it ships zero bytes and
        # cannot become a false affordance. It sits between search and the
        # account control, which is where the future control belongs.
        template = Path('templates/base.html').read_text(encoding='utf-8')
        self.assertIn('PS-SHELL-001 reserved Add slot', template)
        actions = template.split('class="platform-actions"', 1)[1]
        self.assertLess(
            actions.index('PS-SHELL-001 reserved Add slot'),
            actions.index('class="platform-account"'),
        )

    def test_legacy_owner_workspace_keeps_the_unconverged_shell(self):
        """Architecture section 6 wants one component set. /app cannot join
        it while tests/test_owner_home.py locks that render byte for byte —
        including the content fingerprints of style.css, site-search.js and
        mobile-nav.js. The fork is therefore deferred, and this test pins the
        deferral so it is visible rather than assumed."""
        originals = {
            key: app.config.get(key)
            for key in ('PEERSLATE_ALLOW_DEV_IDENTITY', 'PEERSLATE_DEV_USER_KEY')
        }
        app.config['PEERSLATE_ALLOW_DEV_IDENTITY'] = True
        app.config['PEERSLATE_DEV_USER_KEY'] = 'shell-test-owner'
        try:
            legacy = self.client.get('/app', base_url='http://localhost')
        finally:
            for key, value in originals.items():
                if value is None:
                    app.config.pop(key, None)
                else:
                    app.config[key] = value

        self.assertEqual(legacy.status_code, 200)
        body = legacy.get_data(as_text=True)
        self.assertNotIn('public-navigation.css', body)
        self.assertIn('js/site-search.js', body)
        self.assertIn('js/mobile-nav.js', body)
        for shell_only in ('platform-roomswitcher', 'platform-account',
                           'platform-room-title', 'data-global-tabsource',
                           'PS-SHELL-001 reserved Add slot'):
            self.assertNotIn(shell_only, body)

    def test_sitemap_contains_only_current_canonical_public_routes(self):
        response = self.client.get(
            '/sitemap.xml',
            base_url='https://peerslate.com',
        )
        self.assertEqual(response.status_code, 200)
        root = ET.fromstring(response.get_data(as_text=True))
        namespace = {'sitemap': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        locations = [
            item.text
            for item in root.findall('sitemap:url/sitemap:loc', namespace)
        ]
        expected_paths = [
            '/',
            '/experience',
            '/petec/my-story',
            '/petec/skills',
            '/petec/resume',
            '/petec/slate-board',
            '/peerslate',
            '/petec/about',
            '/petec/hobbies',
            '/petec/contact',
            # PS-COMMUNITY-AUTH-WALL-001: no members-only /the-slate route
            # belongs in the public sitemap.
            # PS-INTERVIEW-STUDIO-AUTHENTICATED-EXPERIENCE-001: sign-in is
            # required for Interview Studio (architecture 04 section 1), so
            # /interview-studio is unconditionally removed from the public
            # sitemap -- see tests/test_search_visibility.py for the
            # matching robots.txt Disallow coverage.
            '/career-search',
            '/my-network',
            '/explore-profiles',
            '/for-recruiters',
        ]
        self.assertEqual(
            locations,
            [f'https://peerslate.com{path}' for path in expected_paths],
        )


if __name__ == '__main__':
    unittest.main()

import hashlib
import json
from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from app import app
from identity import AuthenticationRequired
from services.database_service import DatabaseServiceError
from services.owner_home_service import (
    MAX_PAYLOAD_BYTES,
    OwnerHomeContractError,
    OwnerHomeService,
    OwnerHomeViewModel,
)


OWNER_A_PROFILE = "11111111-1111-1111-1111-111111111111"
OWNER_B_PROFILE = "22222222-2222-2222-2222-222222222222"
FAILED_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
PROPOSAL_A = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
READY_A = "cccccccc-cccc-cccc-cccc-cccccccccccc"
MOMENT_A = "dddddddd-dddd-dddd-dddd-dddddddddddd"
FAILED_B = "eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee"

# PS-HOME-FRONTEND-001 fix round 1, delta 3: real byte-for-byte baseline for
# the flag-off /app render, captured from `origin/main` at
# d2592f08056e09629a302966b47fa8ff92517d8e (this package's exact activation
# base) using the same GET /app request the test below issues. Substring
# checks alone let base.html's standalone_owner_shell conditionals ship
# residual whitespace/comment bytes on every route without failing; this
# hash makes any such drift a hard failure. Recapture deliberately (never to
# silence a real regression) only when `templates/owner_workspace.html` or
# the non-standalone branch of `templates/base.html` legitimately changes.
# PS-AUTH-CALLBACK-001 deliberately adds one early script tag to private /app
# and /auth routes; this authorized security behavior is the sole byte delta.
# Supported static URLs now carry an automatic ?v=<12-hex content hash>
# instead of hand-typed tokens (see _stamp_static_asset_version in app.py);
# the render is otherwise byte-for-byte the released workspace. These golden
# values include the fixed-width image and document version tokens.
# PS-PUBLIC-NAV-001 leaves the flag-off owner controls and legacy navigation
# unchanged, but its public/owner Jinja branch adds whitespace bytes to this
# shared-base render. The golden value was deliberately recaptured after
# confirming the owner branch still uses the legacy assets and destinations.
# PS-SIGNIN-EXPERIENCE-001 edits static/css/style.css and static/css/owner-app.css
# (mobile header ceiling; waking-state rules). Neither adds markup to this
# render, but both are linked by it, so each contributes a different automatic
# ?v= content token. Recaptured only after proving that normalizing those two
# 12-hex tokens back to their origin/main values reproduces the previous
# hash exactly, and that the byte length is unchanged at 18214.
# PS-AUTH-JOURNEY-REPAIR-001 changes only the callback script's content token
# in this locked render. The explicit normalization assertion below proves its
# 12 byte `?v=` delta is the sole rendered difference from the verified base;
# no owner-home markup, layout, destination, or control semantics changed.
# The auth-pill header repair changes only style.css, so its content token is
# the sole new delta; normalizing it back reproduces the previous locked hash,
# which in turn normalizes back to the verified base through the callback token.
# The 2026-08-03 owner-directed PS-THEME-002 follow-up intentionally removes
# the shared dark-theme bootstrap, controls, and script from every default
# render, including this legacy /app fallback. The owner workspace content,
# destinations, and semantics remain unchanged. These values recapture that
# bounded light-only shell; the asset-token normalization proof still applies.
# The 2026-08-03 dark-theme pause follow-up closes the routes into dark that
# the first pass did not reach: the Slate Studio shell's own stored-preference
# replay and switch, the toggle script's own gate, the Control Room's
# operating-system-driven variant, and the missing color-scheme declaration.
# PS-OPPORTUNITY-SLATE-001 leg 7 (2026-08-05): Pete's order added an
# unconditional "Opportunity Slate" link to the main navigation next to
# Workshop's. The /app legacy shell has no mobile menu (base.html gates
# that block on `not is_owner_app_path`), so this render only gains the one
# desktop <li> and its matching nav-search record; the byte length moves
# from 16840 to 17116. The recapture step below proves that markup is the
# ONLY delta: stripping exactly those two additions reproduces the previous
# locked baseline (now FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_SHA256) byte for
# byte, and the older asset-token recaptures continue to chain from there
# unchanged. No other owner workspace markup, layout, destination, or
# control semantics changed.
# PS-COMMUNITY-AUTH-WALL-001 recapture. The shared base shell's owner-branch
# header search index dropped the retired public-Community destinations (six
# legacy entries plus the Living Stream preview) and reworded the single
# Community record for the authenticated audience. That block is the ONLY
# delta in this render: the recapture step below swaps the new Community
# record span back to the retired block and reproduces the previous locked
# baseline (now FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_SHA256) byte for byte,
# and the older recaptures continue to chain from there unchanged. No owner
# workspace markup, layout, destination, or control semantics changed.
FLAG_OFF_APP_RENDER_BYTE_LENGTH = 15777
# PS-SIGNIN-MEMBER-ARRIVAL-001 recapture. The byte LENGTH is unchanged
# (15777) and the sole delta is the easy-auth-callback.js content
# fingerprint, which changed because that script's private-path guard was
# widened to the namespaces that moved behind sign-in. Proven by rendering
# this exact request before and after: the diff is one `?v=` token and
# nothing else. No owner workspace markup, layout, destination, or control
# semantics changed, and the recapture chain below still normalizes that
# token back to reproduce every earlier locked baseline.
FLAG_OFF_APP_RENDER_SHA256 = (
    "e6a4cfc78864dd612663c39971a7c0b3b0bcd394f53e72a6670c829ddcb9f4fd"
)
# The chain intermediates below (PRE_AUTH_WALL, PRE_OPPSLATE_NAV,
# PRE_NAV_WRAP, THEME_PAUSE_BASE, STYLE_BASE) moved for that one reason too:
# each is hashed while the render still carries the new callback token.
# FLAG_OFF_APP_RENDER_PREVIOUS_SHA256 is deliberately NOT recaptured — it is
# the terminal step, taken after the token is normalized back, and it still
# matches the historically locked render byte for byte. That is the proof
# this recapture is an asset fingerprint and not a markup change: if any
# owner workspace byte had moved, the terminal assertion would fail.
FLAG_OFF_APP_RENDER_AUTH_WALL_COMMUNITY_SEARCH_SPAN = b'Visible to signed-in PeerSlate members", "href": "/the-slate", "keys": "the slate hub feed people community goals progress proof connect'
FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_COMMUNITY_SEARCH_SPAN = b'People, interests, goals, and progress", "href": "/the-slate", "keys": "the slate hub feed people community goals progress proof connect"},\n        {"title": "Community \xc2\xb7 My Slate", "sub": "Your goal map", "href": "/the-slate/my-slate", "keys": "my slate goals goal map board whiteboard ideas drafts rooms connections"},\n        {"title": "Community \xc2\xb7 Daily Slate", "sub": "Log what moved forward today", "href": "/the-slate/daily", "keys": "daily slate log progress today streak wins check-in updates"},\n        {"title": "Community \xc2\xb7 My Paths", "sub": "Paths and milestones on My Slate", "href": "/the-slate/my-slate#ts-mypaths", "keys": "paths guided tracks milestones pmp run portfolio join community"},\n        {"title": "Feed \xc2\xb7 People & Interests", "sub": "The living board of goals and moments", "href": "/the-slate", "keys": "feed activity progress updates community posts milestones people interests board corkboard notes"},\n        {"title": "Feed \xc2\xb7 Pulse", "sub": "Community momentum", "href": "/the-slate/pulse", "keys": "pulse trending stats momentum numbers skills goals"},\n        {"title": "Feed \xc2\xb7 Break", "sub": "Step back and recharge", "href": "/the-slate/break", "keys": "break recharge rest quotes shout-outs spark"},\n        {"title": "Feed Preview \xc2\xb7 Living Stream", "sub": "A design preview of PeerSlate\'s next Feed \xe2\x80\x94 sample data only", "href": "/feed-living-stream", "keys": "feed preview living stream design concept voice ai capture publish'
FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_BYTE_LENGTH = 17116
FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_SHA256 = (
    "69810cc0f530ae83f7d043593b63e61a87bfe4609d2e504814f5a9773ba59d90"
)
FLAG_OFF_APP_RENDER_OPPSLATE_NAV_LI = (
    b'<li><a href="/opportunity-slate" >Opportunity Slate</a></li>'
)
FLAG_OFF_APP_RENDER_OPPSLATE_NAV_SEARCH_RECORD = (
    b'        {"title": "Opportunity Slate", "sub": "See how your evidence '
    b'lines up with a role", "href": "/opportunity-slate", "keys": '
    b'"opportunity slate role job posting alignment requirements evidence '
    b'match analysis"},\n'
)
# For THIS render the only change is one added declaration in static/css/style.css,
# so the byte length is unchanged at 16840 (of the pre-oppslate-nav baseline)
# and the sole delta is that file's automatic ?v= content token. The
# normalization chain below proves it: swapping the new style token back
# reproduces the previous locked hash exactly, and the older recaptures
# still chain from there. No owner workspace markup, layout, destination, or
# control semantics changed.
FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH = 16840
FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_SHA256 = (
    "320d2582049eb1bb2788d229d8bd320e4acae0381f8f32d63fb52e710ec6604d"
)
# Audit fix F3 (2026-08-04) recapture. static/css/style.css gained a
# flex-wrap rule inside its existing max-width:743px mobile block, so the
# mobile platform nav wraps instead of slicing the current page's own label
# in half. That is a stylesheet content change and nothing else: the only
# delta in THIS render is style.css's automatic ?v= content token, and the
# first normalization step below swaps it back to reproduce the previously
# locked hash byte for byte. No /app markup, layout, destination, or control
# semantics changed.
FLAG_OFF_APP_RENDER_PRE_NAV_WRAP_SHA256 = (
    "8077126be183c8202a31a25c5820dc043bd7e3da59a5d40aa6f926ad79632b74"
)
FLAG_OFF_APP_RENDER_THEME_PAUSE_BASE_SHA256 = (
    "219a0f6f7051ceadf4b42139397d85c643a17b4041c63f0b383df8bbee2affbc"
)
FLAG_OFF_APP_RENDER_STYLE_BASE_SHA256 = (
    "99684daeb559ed6e5289d42df4628092285b73c442713848d604e4dace4ae487"
)
FLAG_OFF_APP_RENDER_PREVIOUS_SHA256 = (
    "073aeba498b180fa69d48a3baae0090b6de89f146574aa717c1c29d827e20815"
)
FLAG_OFF_CALLBACK_VERSION = b"bfd4097e46c7"
FLAG_OFF_CALLBACK_PREVIOUS_VERSION = b"9a8e38ddf7ba"
FLAG_OFF_STYLE_VERSION = b"2b76a653fdca"
FLAG_OFF_STYLE_PRE_NAV_WRAP_VERSION = b"ee65b37f38c5"
FLAG_OFF_STYLE_PRE_THEME_PAUSE_VERSION = b"0b1b477c07af"
FLAG_OFF_STYLE_PREVIOUS_VERSION = b"62c0e8511b80"


def owner_row(profile_key=OWNER_A_PROFILE, display_name="Owner A", token="01" * 8):
    return {
        "profile_key": profile_key,
        "display_name": display_name,
        "profile_row_version": token,
    }


def review_row(item_key, kind, status, minute, token):
    return {
        "item_key": item_key,
        "review_kind": kind,
        "created_at_utc": f"2026-07-20T10:{minute:02d}:00",
        "updated_at_utc": f"2026-07-20T10:{minute + 1:02d}:00",
        "version_token": token * 8,
        "status": status,
    }


def moment_row(moment_key=MOMENT_A, title="A real confirmed Moment"):
    return {
        "moment_key": moment_key,
        "confirmed_version": 2,
        "title": title,
        "occurred_on": "2026-07-19",
        "updated_at_utc": "2026-07-20T10:40:00",
        "version_token": "05" * 8,
        "status": "confirmed",
    }


def complete_result_sets():
    return [
        [owner_row()],
        [
            review_row(FAILED_A, "voice_draft_failed", "failed", 1, "02"),
            review_row(
                PROPOSAL_A, "moment_proposal_pending", "proposal", 2, "03"
            ),
            review_row(READY_A, "voice_draft_ready", "needs_review", 3, "04"),
        ],
        [moment_row()],
    ]


class OwnerHomeServiceTests(unittest.TestCase):
    def setUp(self):
        self.database = Mock()
        self.database.execute_procedure.return_value = complete_result_sets()
        self.clock = lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc)
        self.service = OwnerHomeService(database=self.database, clock=self.clock)
        self.identity = SimpleNamespace(user_key="owner-a")

    def payload(self):
        return self.service.get_home(self.identity).to_dict()

    def test_schema_shape_limits_and_server_owned_availability(self):
        payload = self.payload()

        self.assertEqual(payload["schema_version"], "owner-home.v1")
        self.assertEqual(payload["owner"]["profile_key"], OWNER_A_PROFILE)
        self.assertEqual(len(payload["review_items"]), 3)
        self.assertEqual(payload["recent_moment"]["moment_key"], MOMENT_A)
        self.assertIsNone(payload["resurfaced_moment"])
        self.assertIsNone(payload["noticed_item"])
        self.assertIsNone(payload["connection_item"])
        self.assertEqual(
            payload["availability"],
            {
                "resurfaced_moment": {"state": "coming_later"},
                "noticed_item": {"state": "coming_later"},
                "connection_item": {"state": "coming_later"},
            },
        )
        encoded = json.dumps(payload, separators=(",", ":")).encode()
        self.assertLessEqual(len(encoded), MAX_PAYLOAD_BYTES)

    def test_one_core_query_and_no_optional_member_data_adapters(self):
        self.payload()

        self.database.execute_procedure.assert_called_once_with(
            "usp_GetOwnerHomeForOwner", [("@UserKey", "owner-a")]
        )

    def test_review_order_destinations_and_fixed_owner_safe_summaries(self):
        reviews = self.payload()["review_items"]

        self.assertEqual(
            [item["review_kind"] for item in reviews],
            [
                "voice_draft_failed",
                "moment_proposal_pending",
                "voice_draft_ready",
            ],
        )
        self.assertEqual(reviews[0]["destination"], f"/app/capture?voice={FAILED_A}")
        self.assertEqual(
            reviews[1]["destination"], f"/app/moments/{PROPOSAL_A}/review"
        )
        self.assertNotIn("transcript", json.dumps(reviews).lower())
        self.assertNotIn("blob", json.dumps(reviews).lower())

    def test_state_version_is_stable_and_changes_with_selected_state(self):
        first = self.payload()["state_version"]
        second = self.payload()["state_version"]
        self.assertEqual(first, second)

        changed = complete_result_sets()
        changed[1][0]["version_token"] = "99" * 8
        self.database.execute_procedure.return_value = changed
        self.assertNotEqual(first, self.payload()["state_version"])

    def test_next_step_uses_review_then_recent_then_capture(self):
        self.assertEqual(self.payload()["next_step"]["destination"], f"/app/capture?voice={FAILED_A}")

        no_reviews = complete_result_sets()
        no_reviews[1] = []
        self.database.execute_procedure.return_value = no_reviews
        self.assertEqual(
            self.payload()["next_step"]["destination"],
            f"/app/moments/{MOMENT_A}/review",
        )

        empty = complete_result_sets()
        empty[1] = []
        empty[2] = []
        self.database.execute_procedure.return_value = empty
        self.assertEqual(self.payload()["next_step"]["destination"], "/app/capture")

    def test_unknown_columns_kinds_statuses_and_extra_rows_fail_closed(self):
        cases = []

        extra_owner = complete_result_sets()
        extra_owner[0][0]["email"] = "private@example.invalid"
        cases.append(extra_owner)

        extra_review = complete_result_sets()
        extra_review[1][0]["transcript"] = "PRIVATE TRANSCRIPT"
        cases.append(extra_review)

        bad_kind = complete_result_sets()
        bad_kind[1][0]["review_kind"] = "unreleased_workflow"
        cases.append(bad_kind)

        bad_status = complete_result_sets()
        bad_status[1][0]["status"] = "confirmed"
        cases.append(bad_status)

        too_many = complete_result_sets()
        too_many[1].append(
            review_row(
                "ffffffff-ffff-ffff-ffff-ffffffffffff",
                "voice_draft_ready",
                "needs_review",
                4,
                "06",
            )
        )
        cases.append(too_many)

        extra_moment = complete_result_sets()
        extra_moment[2].append(
            moment_row("99999999-9999-9999-9999-999999999999", "Another")
        )
        cases.append(extra_moment)

        for result_sets in cases:
            with self.subTest(case=cases.index(result_sets)):
                self.database.execute_procedure.return_value = result_sets
                with self.assertRaises(OwnerHomeContractError):
                    self.payload()

    def test_payload_cap_rejects_oversized_view_model(self):
        view_model = OwnerHomeViewModel(
            owner={"profile_key": OWNER_A_PROFILE, "display_name": "X" * 70000},
            generated_at="2026-07-20T11:00:00Z",
            state_version="a" * 64,
            capture_action={
                "action_kind": "capture",
                "destination": "/app/capture",
                "availability": {"state": "available"},
                "label": "Capture something",
            },
            review_items=(),
            recent_moment=None,
            next_step={
                "action_kind": "start_text_capture",
                "label": "Start a new Capture",
                "reason": "Capture something you want to remember.",
                "destination": "/app/capture",
                "availability": {"state": "available"},
            },
        )
        with self.assertRaisesRegex(OwnerHomeContractError, "payload limit"):
            view_model.to_dict()

    def test_serializer_rejects_unknown_internal_action_fields(self):
        view_model = self.service.get_home(self.identity)
        object.__setattr__(
            view_model,
            "capture_action",
            {**view_model.capture_action, "private_count": 17},
        )
        with self.assertRaisesRegex(OwnerHomeContractError, "Capture action shape"):
            view_model.to_dict()

    def test_two_owner_serialized_byte_canaries_do_not_bleed(self):
        payload_a = self.payload()
        bytes_a = json.dumps(payload_a, sort_keys=True).encode()

        owner_b = [
            [owner_row(OWNER_B_PROFILE, "Owner B", "10" * 8)],
            [review_row(FAILED_B, "voice_draft_failed", "failed", 5, "11")],
            [],
        ]
        self.database.execute_procedure.return_value = owner_b
        payload_b = self.service.get_home(
            SimpleNamespace(user_key="owner-b")
        ).to_dict()
        bytes_b = json.dumps(payload_b, sort_keys=True).encode()

        self.assertIn(OWNER_A_PROFILE.encode(), bytes_a)
        self.assertNotIn(OWNER_B_PROFILE.encode(), bytes_a)
        self.assertIn(OWNER_B_PROFILE.encode(), bytes_b)
        self.assertNotIn(OWNER_A_PROFILE.encode(), bytes_b)
        self.assertNotIn(FAILED_A.encode(), bytes_b)

    def test_missing_identity_or_result_set_shape_fails_closed(self):
        with self.assertRaises(OwnerHomeContractError):
            self.service.get_home(SimpleNamespace(user_key=""))

        for result_sets in ([], [[]], [[], [], []], [[owner_row()], []]):
            with self.subTest(result_sets=result_sets):
                self.database.execute_procedure.return_value = result_sets
                with self.assertRaises(OwnerHomeContractError):
                    self.service.get_home(self.identity)


class OwnerHomeRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_OWNER_HOME_ENABLED")
        self.original_dev_user_key = app.config.get("PEERSLATE_DEV_USER_KEY")
        self.original_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = False

    def tearDown(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = self.original_flag
        app.config["PEERSLATE_DEV_USER_KEY"] = self.original_dev_user_key
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_dev_identity

    def view_model(self):
        database = Mock()
        database.execute_procedure.return_value = complete_result_sets()
        return OwnerHomeService(
            database=database,
            clock=lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc),
        ).get_home(SimpleNamespace(user_key="owner-a"))

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_off_is_neutral_404_before_identity_or_retrieval(
        self, identity, home_service
    ):
        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "not_found"})
        identity.assert_not_called()
        home_service.get_home.assert_not_called()

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_on_anonymous_is_json_401_before_home_read(
        self, identity, home_service
    ):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        identity.side_effect = AuthenticationRequired("PRIVATE IDENTITY DETAIL")

        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json(), {"error": "authentication_required"})
        self.assertNotIn(b"PRIVATE", response.data)
        home_service.get_home.assert_not_called()

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_flag_on_owner_gets_bounded_no_store_json(self, identity, home_service):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        resolved = SimpleNamespace(user_key="owner-a")
        identity.return_value = resolved
        home_service.get_home.return_value = self.view_model()

        response = self.client.get("/api/v1/owner/home")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["schema_version"], "owner-home.v1")
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertLessEqual(len(response.data), MAX_PAYLOAD_BYTES)
        home_service.get_home.assert_called_once_with(resolved)

    @patch("owner_routes.owner_home_service")
    @patch("owner_routes.get_current_identity")
    def test_contract_or_database_failure_is_content_free_503(
        self, identity, home_service
    ):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        identity.return_value = SimpleNamespace(user_key="owner-a")
        for error in (
            OwnerHomeContractError("PRIVATE BODY"),
            DatabaseServiceError("PRIVATE SQL DETAIL"),
        ):
            with self.subTest(error=type(error).__name__):
                home_service.get_home.side_effect = error
                response = self.client.get("/api/v1/owner/home")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.get_json(), {"error": "unavailable"})
                self.assertNotIn(b"PRIVATE", response.data)

    def test_flag_off_app_render_is_byte_identical_to_existing_workspace(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = "existing-owner"
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        # The private workspace render is no-store: the rendered bytes below
        # stay identical to the released baseline, only the cache policy is
        # hardened so a shared cache cannot retain one member's workspace.
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        # Real byte-for-byte identity (not just substrings): the intentional
        # light-only shared shell and the unchanged owner workspace must match
        # the newly captured bounded baseline exactly.
        self.assertEqual(len(response.data), FLAG_OFF_APP_RENDER_BYTE_LENGTH)
        self.assertEqual(
            hashlib.sha256(response.data).hexdigest(),
            FLAG_OFF_APP_RENDER_SHA256,
        )
        # PS-COMMUNITY-AUTH-WALL-001 recapture step: swapping the reworded
        # Community search record back to the retired public-destination
        # block must reproduce the previously locked baseline byte for byte
        # before the older recapture chain below continues.
        self.assertEqual(
            response.data.count(
                FLAG_OFF_APP_RENDER_AUTH_WALL_COMMUNITY_SEARCH_SPAN
            ),
            1,
        )
        pre_auth_wall_base = response.data.replace(
            FLAG_OFF_APP_RENDER_AUTH_WALL_COMMUNITY_SEARCH_SPAN,
            FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_COMMUNITY_SEARCH_SPAN,
        )
        self.assertEqual(
            len(pre_auth_wall_base), FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_BYTE_LENGTH
        )
        self.assertEqual(
            hashlib.sha256(pre_auth_wall_base).hexdigest(),
            FLAG_OFF_APP_RENDER_PRE_AUTH_WALL_SHA256,
        )
        # PS-OPPORTUNITY-SLATE-001 leg 7 recapture step: the desktop nav <li>
        # and its nav-search record are the only new bytes this leg adds to
        # the /app render (no mobile menu here to touch). Stripping exactly
        # those two additions must reproduce the previously locked baseline
        # byte for byte before the older asset-token chain below continues.
        self.assertEqual(
            pre_auth_wall_base.count(FLAG_OFF_APP_RENDER_OPPSLATE_NAV_LI), 1
        )
        self.assertEqual(
            pre_auth_wall_base.count(FLAG_OFF_APP_RENDER_OPPSLATE_NAV_SEARCH_RECORD), 1
        )
        pre_oppslate_nav_base = pre_auth_wall_base.replace(
            FLAG_OFF_APP_RENDER_OPPSLATE_NAV_LI, b""
        ).replace(FLAG_OFF_APP_RENDER_OPPSLATE_NAV_SEARCH_RECORD, b"")
        self.assertEqual(
            len(pre_oppslate_nav_base),
            FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH,
        )
        self.assertEqual(
            hashlib.sha256(pre_oppslate_nav_base).hexdigest(),
            FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_SHA256,
        )
        # style.css and the callback script are versioned assets, not Owner
        # Home markup. Their changed content fingerprints are the only allowed
        # flag-off render deltas: normalizing each 12 byte `?v=` token back in
        # turn reproduces the earlier locked baselines exactly. (The values are
        # working-tree content hashes, so Windows CRLF checkout bytes are
        # intentional.)
        self.assertEqual(pre_oppslate_nav_base.count(FLAG_OFF_STYLE_VERSION), 1)
        # Audit fix F3 recapture step: swapping only the style token back
        # must reproduce the previously locked render exactly. If the nav
        # wrap had touched any /app markup, this is where it would fail.
        nav_wrap_base = pre_oppslate_nav_base.replace(
            FLAG_OFF_STYLE_VERSION,
            FLAG_OFF_STYLE_PRE_NAV_WRAP_VERSION,
        )
        self.assertEqual(
            len(nav_wrap_base), FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH
        )
        self.assertEqual(
            hashlib.sha256(nav_wrap_base).hexdigest(),
            FLAG_OFF_APP_RENDER_PRE_NAV_WRAP_SHA256,
        )
        theme_pause_base = nav_wrap_base.replace(
            FLAG_OFF_STYLE_PRE_NAV_WRAP_VERSION,
            FLAG_OFF_STYLE_PRE_THEME_PAUSE_VERSION,
        )
        self.assertEqual(
            len(theme_pause_base), FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH
        )
        self.assertEqual(
            hashlib.sha256(theme_pause_base).hexdigest(),
            FLAG_OFF_APP_RENDER_THEME_PAUSE_BASE_SHA256,
        )
        style_base = theme_pause_base.replace(
            FLAG_OFF_STYLE_PRE_THEME_PAUSE_VERSION,
            FLAG_OFF_STYLE_PREVIOUS_VERSION,
        )
        self.assertEqual(
            len(style_base), FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH
        )
        self.assertEqual(
            hashlib.sha256(style_base).hexdigest(),
            FLAG_OFF_APP_RENDER_STYLE_BASE_SHA256,
        )
        self.assertEqual(style_base.count(FLAG_OFF_CALLBACK_VERSION), 1)
        normalized = style_base.replace(
            FLAG_OFF_CALLBACK_VERSION,
            FLAG_OFF_CALLBACK_PREVIOUS_VERSION,
        )
        self.assertEqual(
            len(normalized), FLAG_OFF_APP_RENDER_PRE_OPPSLATE_NAV_BYTE_LENGTH
        )
        self.assertEqual(
            hashlib.sha256(normalized).hexdigest(),
            FLAG_OFF_APP_RENDER_PREVIOUS_SHA256,
        )
        self.assertIn(b"My PeerSlate", response.data)
        self.assertNotIn(b"owner-home.v1", response.data)
        self.assertNotIn(b"owner-home-shell", response.data)

    def test_owner_home_flag_defaults_off(self):
        self.assertIs(app.config.get("PEERSLATE_OWNER_HOME_ENABLED"), False)


class OwnerHomeHtmlRenderTests(unittest.TestCase):
    """PS-HOME-FRONTEND-001: the flag-on /app HTML render (auth_routes.py)."""

    def setUp(self):
        self.client = app.test_client()
        self.original_flag = app.config.get("PEERSLATE_OWNER_HOME_ENABLED")
        self.original_dev_user_key = app.config.get("PEERSLATE_DEV_USER_KEY")
        self.original_dev_identity = app.config.get("PEERSLATE_ALLOW_DEV_IDENTITY")
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = True
        app.config["PEERSLATE_DEV_USER_KEY"] = "owner-a"
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = True

    def tearDown(self):
        app.config["PEERSLATE_OWNER_HOME_ENABLED"] = self.original_flag
        app.config["PEERSLATE_DEV_USER_KEY"] = self.original_dev_user_key
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = self.original_dev_identity

    def view_model(self, database=None):
        if database is None:
            database = Mock()
            database.execute_procedure.return_value = complete_result_sets()
        return OwnerHomeService(
            database=database,
            clock=lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc),
        ).get_home(SimpleNamespace(user_key="owner-a"))

    @patch("auth_routes.owner_home_service")
    def test_populated_home_renders_bounded_real_data_no_fixtures(self, home_service):
        home_service.get_home.return_value = self.view_model()

        response = self.client.get("/app")
        body = response.data

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"owner-home-shell", body)
        self.assertIn(b"Welcome back, Owner A.", body)
        self.assertIn(b'href="/app/capture"', body)
        self.assertIn(FAILED_A.encode(), body)
        self.assertIn(MOMENT_A.encode(), body)
        self.assertNotIn(b"My PeerSlate", body)
        # D2: no review-artifact fixture/QA pills in the real product.
        self.assertNotIn(b"TEST FIXTURE", body)
        self.assertNotIn(b"PRIVATE FIXTURE", body)
        self.assertNotIn(b"FUTURE DESIGN FIXTURE", body)
        # Dormant categories stay truthful and content-free.
        self.assertIn(b"Coming later", body)
        self.assertNotIn(b"transcript", body.lower())

    @patch("auth_routes.owner_home_service")
    def test_empty_home_states_are_honest_not_generated(self, home_service):
        database = Mock()
        database.execute_procedure.return_value = [
            [owner_row(display_name="Owner Empty")],
            [],
            [],
        ]
        home_service.get_home.return_value = self.view_model(database)

        response = self.client.get("/app")
        body = response.data

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Nothing requires review right now.", body)
        self.assertIn(b"No confirmed Moment to show.", body)
        self.assertIn(b"No confirmed Moment yet", body)
        self.assertNotIn(b"One confirmed", body)
        self.assertIn(b"Start a new Capture", body)

    @patch("auth_routes.owner_home_service")
    def test_recent_moment_note_only_claims_confirmation_when_a_moment_exists(
        self, home_service
    ):
        home_service.get_home.return_value = self.view_model()

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"One confirmed", response.data)
        self.assertNotIn(b"No confirmed Moment yet", response.data)

    @patch("auth_routes.owner_home_service")
    def test_contract_failure_renders_honest_complete_failure_state(
        self, home_service
    ):
        home_service.get_home.side_effect = OwnerHomeContractError("PRIVATE DETAIL")

        response = self.client.get("/app")
        body = response.data

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertIn(b"Owner Home data could not load", body)
        # Capture stays available on failure (independently known destination).
        self.assertIn(b'href="/app/capture"', body)
        self.assertIn(b"data-oh-retry", body)
        self.assertNotIn(b"PRIVATE DETAIL", body)
        # PS-SIGNIN-EXPERIENCE-001 item 2.1: a contract failure is not
        # transient, so it must not borrow the waking treatment, claim the
        # workspace is starting, or ask the browser to come back on its own.
        self.assertNotIn(b"data-ps-waking", body)
        self.assertNotIn(b"workspace-waking.js", body)
        self.assertNotIn(b"is starting", body)
        self.assertNotIn("Retry-After", response.headers)

    @patch("auth_routes.owner_home_service")
    def test_database_failure_renders_transient_waking_state_not_failure(
        self, home_service
    ):
        """PS-SIGNIN-EXPERIENCE-001 item 2.1.

        Azure SQL serverless auto-pauses, so this exception on the first
        signed-in request after an idle period means the database is resuming.
        Presenting that as "HOME DATA FAILED" was untrue.
        """
        home_service.get_home.side_effect = DatabaseServiceError("PRIVATE SQL DETAIL")

        response = self.client.get("/app")
        body = response.data

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["Cache-Control"], "private, no-store")
        self.assertEqual(response.headers["Retry-After"], "5")
        self.assertNotIn(b"PRIVATE SQL DETAIL", body)
        # The truthful transient state, not the contract-failure card.
        self.assertIn(b"Your private workspace is starting", body)
        self.assertIn(b"under a minute", body)
        self.assertNotIn(b"Owner Home data could not load", body)
        self.assertNotIn(b"Home data failed", body)
        # Nothing may be claimed about the member's content.
        self.assertIn(b"published, shared, deleted, or changed.", body)
        self.assertIn(
            b"Your workspace is still starting. Nothing was published, shared,"
            b" or changed.",
            body,
        )

    @patch("auth_routes.owner_home_service")
    def test_waking_state_auto_retry_is_bounded_stoppable_and_polite(
        self, home_service
    ):
        home_service.get_home.side_effect = DatabaseServiceError("unavailable")

        body = self.client.get("/app").data

        # Bounded automatic re-check, driven entirely by server-supplied data.
        self.assertIn(b'data-ps-waking-retry-url="/app"', body)
        self.assertIn(b'data-ps-waking-budget-seconds="90"', body)
        self.assertIn(b"js/workspace-waking.js", body)
        # Announced politely, never as a repeating interrupting alert.
        self.assertIn(b'role="status" aria-live="polite"', body)
        self.assertNotIn(b'class="oh__failure" role="alert"', body)
        # WCAG 2.2 SC 2.2.1: the automatic re-check can be turned off, and the
        # manual route stays server-rendered so the page works without JS.
        self.assertIn(b"data-ps-waking-stop", body)
        self.assertIn(b"Stop checking automatically", body)
        self.assertIn(b'href="/app">Check now</a>', body)

    @patch("auth_routes.owner_home_service")
    def test_successful_home_render_carries_no_waking_markup_or_script(
        self, home_service
    ):
        home_service.get_home.return_value = self.view_model()

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("Retry-After", response.headers)
        self.assertNotIn(b"data-ps-waking", response.data)
        self.assertNotIn(b"workspace-waking.js", response.data)

    def test_flag_on_anonymous_html_redirects_to_sign_in(self):
        app.config["PEERSLATE_ALLOW_DEV_IDENTITY"] = False
        app.config["PEERSLATE_DEV_USER_KEY"] = None

        response = self.client.get("/app")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/sign-in", response.headers["Location"])

    @patch("auth_routes.owner_home_service")
    def test_two_owner_html_serialized_canaries_do_not_bleed(self, home_service):
        # profile_key is intentionally never rendered into the DOM (it is an
        # opaque internal identifier, not display content), so the HTML
        # canaries are the review/Moment item keys and display name that the
        # page actually renders into hrefs and text.
        home_service.get_home.return_value = self.view_model()
        response_a = self.client.get("/app")
        self.assertIn(b"Welcome back, Owner A.", response_a.data)
        self.assertIn(FAILED_A.encode(), response_a.data)
        self.assertIn(MOMENT_A.encode(), response_a.data)

        app.config["PEERSLATE_DEV_USER_KEY"] = "owner-b"
        database_b = Mock()
        database_b.execute_procedure.return_value = [
            [owner_row(OWNER_B_PROFILE, "Owner B", "10" * 8)],
            [review_row(FAILED_B, "voice_draft_failed", "failed", 5, "11")],
            [],
        ]
        home_service.get_home.return_value = OwnerHomeService(
            database=database_b,
            clock=lambda: datetime(2026, 7, 20, 11, 0, tzinfo=timezone.utc),
        ).get_home(SimpleNamespace(user_key="owner-b"))
        response_b = self.client.get("/app")

        self.assertIn(b"Welcome back, Owner B.", response_b.data)
        self.assertIn(FAILED_B.encode(), response_b.data)
        self.assertNotIn(FAILED_A.encode(), response_b.data)
        self.assertNotIn(MOMENT_A.encode(), response_b.data)
        self.assertNotIn(b"Welcome back, Owner A.", response_b.data)


if __name__ == "__main__":
    unittest.main()

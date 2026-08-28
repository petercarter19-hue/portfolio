"""Fake-only ordering and completion checks for the attended broker handoff."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from qa.synthetic_member import sealed_credential_broker as broker
from qa.synthetic_member.contracts import JOURNEY_BY_ID


NOW = datetime(2026, 8, 28, 18, 0, tzinfo=timezone.utc)
ISSUER = "synthetic-tenant.onmicrosoft.com"
AUTH_ISSUER = "https://synthetic-tenant.ciamlogin.com"
EXACT_SAME_ORIGIN_HEADERS = {
    "Origin": "https://peerslate.com",
    "Sec-Fetch-Site": "same-origin",
}
SUBJECTS = (
    "11111111-1111-1111-1111-111111111111",
    "22222222-2222-2222-2222-222222222222",
)


def _forbid_live_outbound(*_args, **_kwargs):
    raise AssertionError("attended broker tests must use fake-only adapters")


def setUpModule():
    global _OUTBOUND_GUARDS
    _OUTBOUND_GUARDS = (
        patch.object(broker.subprocess, "run", side_effect=_forbid_live_outbound),
        patch.object(broker, "urlopen", side_effect=_forbid_live_outbound),
        patch.object(broker, "_start_playwright", side_effect=_forbid_live_outbound),
        patch.object(
            broker.retirement,
            "open_production_connection",
            side_effect=_forbid_live_outbound,
        ),
    )
    for guard in _OUTBOUND_GUARDS:
        guard.start()


def tearDownModule():
    for guard in reversed(_OUTBOUND_GUARDS):
        guard.stop()


def complete_outcome(*, residue=0):
    observations = {
        journey_id: broker.JourneyObservation(
            status="pass", observed_outcome=journey.expected_outcome, note_code="none"
        )
        for journey_id, journey in JOURNEY_BY_ID.items()
    }
    for journey_id, note_code in broker.REQUIRED_CONDITIONAL_OUTCOMES.items():
        observations[journey_id] = broker.JourneyObservation(
            status="conditional", observed_outcome="limitation_recorded", note_code=note_code
        )
    return broker.BrowserOutcome(
        journey_outcomes=observations,
        created_item_counts={"member_a": 1, "member_b": 1},
        active_residue_counts={"member_a": residue, "member_b": 0},
        archived_residue_counts={"member_a": 0, "member_b": 0},
        clean_start_confirmed=True,
    )


class RecordingSession:
    def __init__(self, events, outcome):
        self.events = events
        self.outcome = outcome
        self.cleaned = False

    def auth_issuer(self):
        self.events.append("public_auth_route_derived")
        return broker.SealedValue(AUTH_ISSUER)

    def exercise_canonical_journeys(self, identities):
        self.events.append("all_38_journeys_complete")
        self.aliases = tuple(identity.alias for identity in identities)
        return self.outcome

    def destroy_and_verify(self):
        if self.cleaned:
            return broker.BrowserCleanup(4, True)
        self.events.append("four_contexts_and_root_destroyed")
        self.cleaned = True
        return broker.BrowserCleanup(4, True)


class RecordingBrowser:
    def __init__(self, events, outcome):
        self.events = events
        self.session = RecordingSession(events, outcome)

    def prepare_attended_session(self):
        self.events.extend(("browser_module_executable_preflight", "signed_out_baseline"))
        return self.session


class RecordingGraph:
    def __init__(self, events):
        self.events = events
        self.post_calls = 0

    def resolve_graph_issuer(self):
        self.events.append("tenant_binding_verified")
        if self.events[:2] != ["browser_module_executable_preflight", "signed_out_baseline"]:
            raise AssertionError("Graph routing was derived before browser preflight")
        return broker.SealedValue(ISSUER)

    def create_customer(self, identity, *, graph_issuer):
        del graph_issuer
        self.post_calls += 1
        self.events.append(f"post_{identity.alias}")
        return SUBJECTS[self.post_calls - 1]


class RecordingRetirement:
    def __init__(self, events):
        self.events = events
        self.calls = 0

    def retire(self, _subjects, *, auth_issuer, cutoff):
        del auth_issuer, cutoff
        self.calls += 1
        if not self.events or self.events[-1] != "four_contexts_and_root_destroyed":
            raise AssertionError("retirement ran before final browser cleanup")
        self.events.append("retirement")
        return {"result": "pass", "state": "retired", "counts": {"retired_members": 2}}


class StrictResponse:
    def __init__(self, status=302, headers=None):
        self.status = status
        self.headers = dict(headers or {})
        self.disposed = False

    def dispose(self):
        self.disposed = True


class StrictWorkshopStore:
    def __init__(self):
        self.items = {}
        self.request_log = []
        self._next = 0
        self.foreign_response = None

    def create(self, owner, marker):
        self._next += 1
        key = f"opaque-{self._next}"
        self.items[key] = {"owner": owner, "marker": marker, "version": f"v{self._next}", "status": "active"}
        return key

    def version(self, key):
        return self.items[key]["version"]

    def bump_version(self, key):
        self.items[key]["version"] = f"{self.items[key]['version']}-next"

    def visible_markers(self, owner, page_url):
        parsed = urlparse(page_url)
        if parsed.path != "/app/workshop" or owner is None:
            return set()
        query = parse_qs(parsed.query)
        requested = query.get("item", [])
        status = query.get("status", ["active"])[0]
        candidates = self.items.items()
        if requested:
            candidates = ((key, self.items[key]) for key in requested if key in self.items)
        return {
            item["marker"]
            for _key, item in candidates
            if item["owner"] == owner and item["status"] == status
        }

    def selected_owned_item(self, owner, page_url):
        parsed = urlparse(page_url)
        query = parse_qs(parsed.query)
        keys = query.get("item", [])
        if len(keys) == 1 and keys[0] in self.items and self.items[keys[0]]["owner"] == owner:
            return keys[0]
        path_parts = parsed.path.split("/")
        if len(path_parts) >= 5 and path_parts[-2] == "items":
            key = path_parts[-1]
            if key in self.items and self.items[key]["owner"] == owner:
                return key
        if len(path_parts) >= 6 and path_parts[-3] == "items":
            key = path_parts[-2]
            if key in self.items and self.items[key]["owner"] == owner:
                return key
        return None


class StrictLocator:
    def __init__(self, page, selector=None, *, role=None, name=None):
        self.page = page
        self.selector = selector
        self.role = role
        self.name = name

    def count(self):
        if self.selector == ".wk-status-banner--preview":
            return int(self.page.context.owner is None and urlparse(self.page.url).path == "/app/workshop")
        if self.selector == "input[name='expected_row_version']":
            return int(self.page.store.selected_owned_item(self.page.context.owner, self.page.url) is not None)
        if self.selector == broker.AUTHENTICATED_WORKSHOP_CONTROL:
            return int(self.page.context.owner is not None)
        if self.selector == ".wk-detail":
            return int(
                self.page.store.selected_owned_item(self.page.context.owner, self.page.url)
                is not None
            )
        if self.role == "text":
            return int(self.name in self.page.store.visible_markers(self.page.context.owner, self.page.url))
        return 1

    def fill(self, value):
        self.page.fields[self.selector] = value

    def check(self):
        self.page.checked.add(self.selector)

    def input_value(self):
        key = self.page.store.selected_owned_item(self.page.context.owner, self.page.url)
        if key is None:
            raise AssertionError("version was requested outside an owned item")
        return self.page.store.version(key)

    def get_attribute(self, name):
        if self.role == "link" and self.name == "View in My Information" and name == "href":
            return f"/app/workshop?item={self.page.saved_key}"
        return None

    def click(self):
        if self.role == "button":
            self.page.click_button(self.name)
        elif self.selector == "button[name='save_action'][value='confirm']":
            self.page.save_current()


class StrictRequest:
    def __init__(self, page):
        self.page = page

    def post(self, endpoint, *, form, headers, fail_on_status_code, max_redirects):
        assert fail_on_status_code is False
        assert max_redirects == 0
        parsed = urlparse(endpoint)
        assert parsed.scheme == "https" and parsed.hostname == "peerslate.com"
        parts = parsed.path.split("/")
        assert parts[:4] == ["", "app", "workshop", "items"]
        key = parts[4]
        item = self.page.store.items[key]
        assert item["owner"] != self.page.context.owner
        if len(parts) == 5:
            assert form["save_action"] == "confirm"
            assert form["expected_row_version"] == item["version"]
            kind = "update"
        else:
            assert parts[5] == "delete"
            assert form["confirm_delete"] == "delete"
            assert form["expected_row_version"] == item["version"]
            kind = "delete"
        self.page.store.request_log.append(("POST", kind, parsed.path, key, dict(headers)))
        if headers != EXACT_SAME_ORIGIN_HEADERS:
            return StrictResponse(403)
        fault = self.page.store.foreign_response
        if fault is not None:
            if fault.get("session_lost"):
                self.page.context.owner = None
            return StrictResponse(fault["status"], fault.get("headers"))
        if kind == "update":
            return StrictResponse(200)
        return StrictResponse(
            302, {"location": f"/app/workshop?item={key}&error=changed"}
        )


class StrictContext:
    def __init__(self, store):
        self.store = store
        self.owner = None
        self.closed = False
        self.pages = []

    @property
    def request(self):
        return StrictRequest(self.pages[-1])

    def new_page(self):
        page = StrictPage(self, self.store)
        self.pages.append(page)
        return page

    def clear_cookies(self):
        self.owner = None

    def close(self):
        self.closed = True


class StrictPage:
    def __init__(self, context, store):
        self.context = context
        self.store = store
        self.url = "https://peerslate.com/"
        self.fields = {}
        self.checked = set()
        self.saved_key = None
        self.visited = []
        self.sign_in_arrivals = 0
        self.explicit_workshop_arrivals = 0
        self._requires_explicit_workshop_arrival = False

    def goto(self, url, *, wait_until):
        del wait_until
        self.visited.append(("GET", url))
        if "/.auth/login/" in url:
            self.url = f"{AUTH_ISSUER}/authorize"
        elif "/.auth/logout" in url:
            self.context.owner = None
            self.url = "https://peerslate.com/"
        else:
            if self._requires_explicit_workshop_arrival:
                assert url == "https://peerslate.com/app/workshop"
                self.explicit_workshop_arrivals += 1
                self._requires_explicit_workshop_arrival = False
            self.url = url

    def locator(self, selector):
        return StrictLocator(self, selector)

    def get_by_text(self, text, *, exact):
        assert exact is True
        return StrictLocator(self, role="text", name=text)

    def get_by_role(self, role, *, name):
        return StrictLocator(self, role=role, name=name)

    def wait_for_url(self, _pattern, *, timeout):
        del timeout
        arrival_url = "https://peerslate.com/app"
        assert _pattern.search(arrival_url)
        email = self.fields["input[type='email']"]
        self.context.owner = "member_a" if email.endswith("member_a@synthetic-tenant.onmicrosoft.com") else "member_b"
        self.url = arrival_url
        self.sign_in_arrivals += 1
        self._requires_explicit_workshop_arrival = True

    def reload(self, *, wait_until):
        del wait_until

    def close(self):
        return None

    def click_button(self, name):
        if name == "Continue":
            return None
        key = self.store.selected_owned_item(self.context.owner, self.url)
        if name == "Archive":
            assert key is not None
            self.store.items[key]["status"] = "archived"
            self.store.bump_version(key)
            return
        if name == "Restore":
            assert key is not None
            self.store.items[key]["status"] = "active"
            self.store.bump_version(key)
            return
        if name == "Delete permanently":
            assert key is not None and "input[name='confirm_delete']" in self.checked
            del self.store.items[key]
            self.url = "https://peerslate.com/app/workshop"
            return
        raise AssertionError(f"unexpected button {name}")

    def save_current(self):
        key = self.store.selected_owned_item(self.context.owner, self.url)
        if key is None:
            key = self.store.create(self.context.owner, self.fields["#wk-title"])
        else:
            self.store.bump_version(key)
        self.saved_key = key
        self.url = f"https://peerslate.com/app/workshop/items/{key}/saved"


class StrictBrowser:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class StrictPlaywright:
    def __init__(self):
        self.stopped = False

    def stop(self):
        self.stopped = True


class StrictBrowserAdapter:
    def __init__(self, session):
        self.session = session

    def prepare_attended_session(self):
        return self.session


class StrictGraph:
    def __init__(self):
        self.calls = 0

    def resolve_graph_issuer(self):
        return broker.SealedValue(ISSUER)

    def create_customer(self, _identity, *, graph_issuer):
        del graph_issuer
        subject = SUBJECTS[self.calls]
        self.calls += 1
        return subject


class NoRetirement:
    def __init__(self):
        self.calls = 0

    def retire(self, *_args, **_kwargs):
        self.calls += 1
        raise AssertionError("retirement must not run after an adverse browser result")


class StrictRetirement:
    """Accept only a structurally complete, already-cleaned fake lifecycle."""

    def __init__(self, contexts, browser_process, playwright, temporary_root):
        self.contexts = contexts
        self.browser_process = browser_process
        self.playwright = playwright
        self.temporary_root = Path(temporary_root)
        self.calls = 0
        self.cleanup_verified = False

    def retire(self, _subjects, *, auth_issuer, cutoff):
        del auth_issuer, cutoff
        self.calls += 1
        assert all(context.closed for context in self.contexts.values())
        assert self.browser_process.closed and self.playwright.stopped
        assert not self.temporary_root.exists()
        self.cleanup_verified = True
        return {"result": "pass", "state": "retired", "counts": {"retired_members": 2}}


class AttendedHandoffTests(unittest.TestCase):
    @staticmethod
    def _preflight_outcomes():
        return {
            "clean_client_a_start": broker._pass_observation("clean_client_a_start"),
            "clean_client_b_start": broker._pass_observation("clean_client_b_start"),
            "clean_signed_out_control_start": broker._pass_observation(
                "clean_signed_out_control_start"
            ),
            "signed_out_private_baseline": broker._pass_observation(
                "signed_out_private_baseline"
            ),
        }

    def _strict_session(self, temporary_root, *, store=None):
        store = store or StrictWorkshopStore()
        contexts = {
            name: StrictContext(store)
            for name in ("member_a", "member_b", "signed_out", "switch")
        }
        browser_process = StrictBrowser()
        playwright = StrictPlaywright()
        session = broker._PlaywrightAttendedSession(
            adapter=broker.PlaywrightBrowserAdapter(playwright_factory=lambda: None),
            contexts=contexts,
            browser=browser_process,
            playwright=playwright,
            workspace=Path(temporary_root),
            auth_issuer=broker.SealedValue(AUTH_ISSUER),
            signed_out_page=contexts["signed_out"].new_page(),
            preflight_outcomes=self._preflight_outcomes(),
        )
        return store, contexts, browser_process, playwright, session

    @staticmethod
    def _strict_identities():
        return broker._generate_identities(
            broker.SealedValue(ISSUER),
            run_id="qa-20260828-0001",
            choice=lambda _alphabet: "z",
        )

    def test_strict_fake_exercises_every_journey_with_real_route_and_mutation_contracts(self):
        with TemporaryDirectory() as temporary_root:
            store, contexts, browser_process, playwright, session = self._strict_session(
                temporary_root
            )
            retirement = StrictRetirement(
                contexts, browser_process, playwright, temporary_root
            )
            captured = {}
            original_exercise = session.exercise_canonical_journeys

            def capture_outcome(run_identities):
                captured["outcome"] = original_exercise(run_identities)
                return captured["outcome"]

            session.exercise_canonical_journeys = capture_outcome
            report = broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=StrictGraph(),
                browser=StrictBrowserAdapter(session),
                retirement_adapter=retirement,
                choice=lambda _alphabet: "z",
            )
            outcome = captured["outcome"]
            # The only report fields are structural outcomes/counts; it contains
            # no fake identifiers, secrets, private page state, or item handles.
            self.assertEqual(set(report), {"result", "state", "counts"})
            self.assertEqual(report["result"], "conditional")
            self.assertEqual(report["counts"]["canonical_journeys"], len(JOURNEY_BY_ID))
            self.assertEqual(report["counts"]["conditional_journeys"], 8)
            cleanup = session.destroy_and_verify()

            self.assertEqual(set(outcome.journey_outcomes), set(JOURNEY_BY_ID))
            conditionals = {
                "member_a_cannot_update_member_b": "neutral_denial_not_distinguishable",
                "member_b_cannot_update_member_a": "neutral_denial_not_distinguishable",
                "member_a_cannot_export_member_b": "feature_surface_unavailable",
                "member_b_cannot_export_member_a": "feature_surface_unavailable",
                "member_a_forged_reference_denied": "feature_surface_unavailable",
                "member_b_forged_reference_denied": "feature_surface_unavailable",
                "member_a_expired_session_safe": "session_expiry_not_controllable",
                "member_b_expired_session_safe": "session_expiry_not_controllable",
            }
            self.assertEqual(
                {
                    journey_id: observation.note_code
                    for journey_id, observation in outcome.journey_outcomes.items()
                    if observation.status == "conditional"
                },
                conditionals,
            )
            self.assertEqual(outcome.active_residue_counts, {"member_a": 0, "member_b": 0})
            self.assertEqual(outcome.archived_residue_counts, {"member_a": 0, "member_b": 0})
            self.assertEqual(store.items, {})
            self.assertEqual(
                [(method, kind) for method, kind, _path, _key, _headers in store.request_log],
                [("POST", "update"), ("POST", "delete"), ("POST", "update"), ("POST", "delete")],
            )
            self.assertEqual(
                {key for _method, _kind, _path, key, _headers in store.request_log},
                {"opaque-1", "opaque-2"},
            )
            self.assertTrue(
                all(
                    headers == EXACT_SAME_ORIGIN_HEADERS
                    for _method, _kind, _path, _key, headers in store.request_log
                )
            )
            all_gets = [url for context in contexts.values() for page in context.pages for method, url in page.visited if method == "GET"]
            self.assertEqual(
                sum(page.sign_in_arrivals for context in contexts.values() for page in context.pages),
                5,
            )
            self.assertEqual(
                sum(page.explicit_workshop_arrivals for context in contexts.values() for page in context.pages),
                5,
            )
            self.assertFalse(any("export" in url for url in all_gets))
            self.assertIn("https://peerslate.com/app/workshop?status=archived", all_gets)
            self.assertFalse(
                any("reference" in parse_qs(urlparse(url).query) for url in all_gets)
            )
            self.assertFalse(any(version in url for url in all_gets for version in ("v1", "v2")))
            self.assertEqual(cleanup, broker.BrowserCleanup(4, True))
            self.assertEqual(retirement.calls, 1)
            self.assertTrue(retirement.cleanup_verified)
            self.assertTrue(browser_process.closed and playwright.stopped)
            self.assertTrue(all(context.closed for context in contexts.values()))

    def test_strict_same_origin_gate_refuses_a_missing_signal(self):
        store = StrictWorkshopStore()
        actor = StrictContext(store)
        actor.owner = "member_a"
        peer_key = store.create("member_b", "safe-peer")
        page = actor.new_page()
        response = actor.request.post(
            f"https://peerslate.com/app/workshop/items/{peer_key}",
            form={
                "title": "safe-actor",
                "wording": "safe-actor-foreign-update",
                "classification": "unclassified",
                "save_action": "confirm",
                "expected_row_version": store.version(peer_key),
            },
            headers={"Origin": "https://peerslate.com"},
            fail_on_status_code=False,
            max_redirects=0,
        )
        self.assertEqual(response.status, 403)
        self.assertEqual(store.items[peer_key]["owner"], "member_b")

    def test_adverse_foreign_mutation_responses_are_indeterminate_and_never_retire(self):
        scenarios = (
            (
                "missing_header_rejected",
                None,
                {"Origin": "https://peerslate.com"},
            ),
            ("unauthenticated", {"status": 401}, None),
            ("forbidden", {"status": 403}, None),
            ("conflict", {"status": 409}, None),
            ("server_failure", {"status": 500}, None),
            ("unexpected_redirect", {"status": 302, "headers": {"location": "/unexpected"}}, None),
            ("session_lost", {"status": 200, "session_lost": True}, None),
        )
        for scenario, response, mutation_headers in scenarios:
            with self.subTest(scenario=scenario), TemporaryDirectory() as temporary_root:
                store, contexts, _browser_process, _playwright, session = self._strict_session(
                    temporary_root
                )
                store.foreign_response = response
                retirement = NoRetirement()
                mutation_headers = mutation_headers or broker.SAME_ORIGIN_MUTATION_HEADERS
                with patch.object(broker, "SAME_ORIGIN_MUTATION_HEADERS", mutation_headers):
                    with self.assertRaisesRegex(
                        broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
                    ):
                        broker.run_broker(
                            run_id="qa-20260828-0001",
                            cutoff=NOW,
                            graph=StrictGraph(),
                            browser=StrictBrowserAdapter(session),
                            retirement_adapter=retirement,
                            choice=lambda _alphabet: "z",
                        )
                self.assertEqual(retirement.calls, 0)
                self.assertTrue(all(context.closed for context in contexts.values()))

    def test_signed_out_residue_cannot_be_reported_as_zero_or_retired(self):
        with TemporaryDirectory() as temporary_root:
            store, contexts, _browser_process, _playwright, session = self._strict_session(
                temporary_root
            )
            marker = "safe-owned-item"
            store.create("member_a", marker)
            residue_page = contexts["member_a"].new_page()
            contexts["member_a"].owner = None

            with self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
            ):
                session._observe_item_residue(residue_page, marker)
            self.assertEqual(len(store.items), 1)

            retirement = NoRetirement()
            session.exercise_canonical_journeys = lambda _identities: session._observe_item_residue(
                residue_page, marker
            )
            with self.assertRaisesRegex(
                broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"
            ):
                broker.run_broker(
                    run_id="qa-20260828-0001",
                    cutoff=NOW,
                    graph=StrictGraph(),
                    browser=StrictBrowserAdapter(session),
                    retirement_adapter=retirement,
                    choice=lambda _alphabet: "z",
                )
            self.assertEqual(retirement.calls, 0)
            self.assertTrue(all(context.closed for context in contexts.values()))

    def test_exact_attended_order_and_pair_coverage(self):
        events = []
        browser_adapter = RecordingBrowser(events, complete_outcome())
        graph = RecordingGraph(events)
        retirement = RecordingRetirement(events)

        report = broker.run_broker(
            run_id="qa-20260828-0001",
            cutoff=NOW,
            graph=graph,
            browser=browser_adapter,
            retirement_adapter=retirement,
        )

        self.assertEqual(browser_adapter.session.aliases, ("member_a", "member_b"))
        self.assertEqual(graph.post_calls, 2)
        self.assertEqual(retirement.calls, 1)
        self.assertEqual(report["counts"]["canonical_journeys"], len(JOURNEY_BY_ID))
        self.assertEqual(events, [
            "browser_module_executable_preflight",
            "signed_out_baseline",
            "public_auth_route_derived",
            "tenant_binding_verified",
            "post_member_a",
            "post_member_b",
            "all_38_journeys_complete",
            "four_contexts_and_root_destroyed",
            "retirement",
        ])

    def test_active_residue_blocks_retirement_after_graph_mutation(self):
        events = []
        retirement = RecordingRetirement(events)
        with self.assertRaisesRegex(broker.BrokerIndeterminate, "sealed_browser_operation_indeterminate"):
            broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=RecordingGraph(events),
                browser=RecordingBrowser(events, complete_outcome(residue=1)),
                retirement_adapter=retirement,
            )
        self.assertEqual(retirement.calls, 0)

    def test_pre_graph_refusal_does_not_hide_browser_cleanup_failure(self):
        events = []
        browser_adapter = RecordingBrowser(events, complete_outcome())

        def cleanup_failure():
            raise broker.BrokerIndeterminate("sealed_browser_cleanup_indeterminate")

        browser_adapter.session.destroy_and_verify = cleanup_failure

        class RefusingGraph:
            def resolve_graph_issuer(self):
                events.append("tenant_binding_refused")
                raise broker.BrokerRefusal("graph_tenant_issuer_mismatch")

            def create_customer(self, *_args, **_kwargs):
                raise AssertionError("Graph customer POST must not run")

        with self.assertRaisesRegex(
            broker.BrokerIndeterminate, "sealed_browser_cleanup_indeterminate"
        ):
            broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=RefusingGraph(),
                browser=browser_adapter,
                retirement_adapter=RecordingRetirement(events),
            )

    def test_default_live_backends_are_not_reached_from_fake_attended_test(self):
        def blocked(*_args, **_kwargs):
            raise AssertionError("outbound backend reached")

        with patch.object(broker.subprocess, "run", side_effect=blocked), patch.object(
            broker, "urlopen", side_effect=blocked
        ), patch.object(broker, "_start_playwright", side_effect=blocked), patch.object(
            broker.retirement, "open_production_connection", side_effect=blocked
        ):
            events = []
            result = broker.run_broker(
                run_id="qa-20260828-0001",
                cutoff=NOW,
                graph=RecordingGraph(events),
                browser=RecordingBrowser(events, complete_outcome()),
                retirement_adapter=RecordingRetirement(events),
            )
        self.assertEqual(result["result"], "conditional")


if __name__ == "__main__":
    unittest.main()

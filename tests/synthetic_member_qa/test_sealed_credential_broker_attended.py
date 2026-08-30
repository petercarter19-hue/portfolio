"""Strict fake-only Workshop F/G journey and residue checks."""

from __future__ import annotations

import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from qa.synthetic_member import sealed_credential_broker as broker
from qa.synthetic_member.sealed_credential_broker import child_worker
from qa.synthetic_member.contracts import JOURNEY_BY_ID


ISSUER = "synthetic-tenant.onmicrosoft.com"
AUTHORIZATION_ORIGIN = "https://synthetic-tenant.ciamlogin.com"
class StrictWorkshopStore:
    """Model saved history separately from row-version concurrency."""

    def __init__(self, *, fault=None, delete_fault=None):
        self.items = {}
        self.fault = fault
        self.delete_fault = delete_fault
        self.delete_attempts = []
        self.deleted_history_lengths = []
        self.version_appends = 0
        self.concurrency_only_bumps = 0
        self._next = 0

    def create(self, owner, marker, wording):
        self._next += 1
        key = f"opaque-{self._next}"
        self.items[key] = {
            "owner": owner,
            "marker": marker,
            "versions": [wording],
            "row_version": 1,
            "status": "active",
        }
        return key

    def row_version(self, key):
        return f"rv-{self.items[key]['row_version']}"

    def append_version(self, key, wording):
        self.items[key]["versions"].append(wording)
        self.items[key]["row_version"] += 1
        self.version_appends += 1

    def bump_concurrency(self, key):
        self.items[key]["row_version"] += 1
        self.concurrency_only_bumps += 1

    def selected_key(self, owner, page_url):
        parsed = urlparse(page_url)
        query = parse_qs(parsed.query)
        candidates = query.get("item", [])
        status = query.get("status", ["active"])[0]
        path = parsed.path.split("/")
        direct_action = False
        if not candidates and len(path) >= 6 and path[1:4] == ["app", "workshop", "items"]:
            candidates = [path[4]]
            direct_action = True
        if len(candidates) != 1:
            return None
        key = candidates[0]
        item = self.items.get(key)
        if item is None or item["owner"] != owner:
            return None
        if not direct_action and item["status"] != status:
            return None
        return key

    def visible_markers(self, owner, page_url):
        parsed = urlparse(page_url)
        if owner is None or parsed.path != "/app/workshop":
            return set()
        query = parse_qs(parsed.query)
        requested = query.get("item", [])
        status = query.get("status", ["active"])[0]
        candidates = self.items.items()
        if requested:
            candidates = (
                (key, self.items[key]) for key in requested if key in self.items
            )
        return {
            item["marker"]
            for _key, item in candidates
            if item["owner"] == owner and item["status"] == status
        }


class StrictLocator:
    def __init__(
        self,
        page,
        kind="unknown",
        *,
        selector=None,
        text=None,
        exact=True,
        row=None,
        slot=None,
    ):
        self.page = page
        self.kind = kind
        self.selector = selector
        self.text = text
        self.exact = exact
        self.row = row
        self.slot = slot

    def _selected_item(self):
        key = self.page.store.selected_key(self.page.context.owner, self.page.url)
        return self.page.store.items.get(key) if key else None

    def _history_rows(self):
        item = self._selected_item()
        if item is None:
            return []
        rows = list(item["versions"])
        if self.page.store.fault != "history_order":
            rows.reverse()
        if self.page.store.fault == "missing_version":
            rows = rows[:-1]
        return rows

    def count(self):
        parsed = urlparse(self.page.url)
        if self.kind == "preview":
            return int(
                self.page.context.owner is None
                and parsed.path == "/app/workshop"
            )
        if self.kind in {"username", "password", "submit"}:
            return int(self.page.url.startswith(AUTHORIZATION_ORIGIN))
        if self.kind == "authenticated":
            return int(
                self.page.context.owner is not None
                and parsed.path == "/app/workshop"
            )
        if self.kind == "row_version":
            return int(self._selected_item() is not None)
        if self.kind == "saved_link":
            return int(self.page.saved_key is not None)
        if self.kind == "marker_text":
            markers = self.page.store.visible_markers(
                self.page.context.owner, self.page.url
            )
            if self.exact:
                return int(self.text in markers)
            return int(any(self.text in marker for marker in markers))
        if self.kind == "deletion_text":
            selected = self._selected_item() is not None
            if self.text == "Permanent deletion":
                return int(selected)
            if self.text == "could not check just now":
                return int(selected and self.page.store.fault == "delete_unavailable")
            if self.text == "Your saved Opportunity Slate cites this item":
                return int(selected and self.page.store.fault == "delete_cited")
            return 0
        if self.kind == "article_detail":
            return int(self._selected_item() is not None)
        if self.kind == "history":
            return int(self._selected_item() is not None)
        if self.kind in {"history_count", "history_note"}:
            return int(self._selected_item() is not None)
        if self.kind == "history_window":
            return int(self.page.store.fault == "history_window")
        if self.kind == "history_versions":
            return len(self._history_rows())
        if self.kind == "history_wordings":
            return 2 if self.row is not None else 0
        if self.kind == "history_wording":
            return int(
                self.row is not None
                and self.slot in {0, 1}
                and self.row < len(self._history_rows())
            )
        if self.kind == "version_label":
            rows = self._history_rows()
            expected = f"Version {len(rows) - self.row}" if self.row is not None else ""
            return int(self.text == expected)
        if self.kind == "downstream_row":
            return int(self._selected_item() is not None)
        if self.kind == "downstream_rows":
            return 5 if self._selected_item() is not None else 0
        if self.kind == "downstream_dd":
            return int(self._selected_item() is not None)
        # Unknown selectors are never optimistic. This is the regression gate
        # against the former fake that returned one for every new selector.
        return 0

    def fill(self, value):
        if self.kind not in {"field", "username", "password"}:
            raise AssertionError(f"unmodelled fill: {self.selector}")
        self.page.fields[self.selector] = value

    def wait_for(self, *, state, timeout):
        if (
            self.kind != "username"
            or state != "visible"
            or timeout != broker.IDENTITY_USERNAME_WAIT_TIMEOUT_MS
            or self.count() != 1
        ):
            raise AssertionError("unmodelled username control wait")

    def element_handle(self):
        if self.kind not in {
            "username",
            "password",
            "field",
            "classification",
            "confirm_delete",
            "save_confirm",
            "button",
        }:
            raise AssertionError(f"unmodelled element_handle: {self.selector}")
        return self

    def evaluate(self, expression, payload):
        del expression
        operation = payload.get("operation") if isinstance(payload, dict) else None
        if operation is not None:
            self.page.assert_canonical_document(payload)
            if operation == "fill":
                self.fill(payload["value"])
            elif operation == "check":
                self.check()
            elif operation == "click":
                self.click()
            else:
                raise AssertionError(f"unmodelled evaluator operation: {operation}")
            return True
        if self.kind not in {"username", "password"}:
            raise AssertionError(f"unmodelled evaluate: {self.selector}")
        parsed = urlparse(self.page.url)
        actual = f"{parsed.scheme}://{parsed.hostname}"
        if actual != payload.get("expectedOrigin"):
            raise RuntimeError("atomic origin refusal")
        if self.kind == "username":
            if payload.get("selector") != broker.IDENTITY_USERNAME_SELECTOR:
                raise AssertionError("unexpected sealed username selector")
            identifier = payload.get("identifier")
            if not isinstance(identifier, str) or not identifier:
                raise AssertionError("missing sealed username")
            self.page.fields[self.selector] = identifier
            return
        secret = payload.get("secret")
        if not isinstance(secret, str) or not secret:
            raise AssertionError("missing sealed password")
        self.page.fields[self.selector] = secret

    def dispose(self):
        if self.kind not in {
            "username",
            "password",
            "field",
            "classification",
            "confirm_delete",
            "save_confirm",
            "button",
        }:
            raise AssertionError(f"unmodelled dispose: {self.selector}")

    def evaluate_all(self, expression, payload):
        self.page.assert_canonical_document(payload)
        operation = payload.get("operation")
        if operation is None and self.kind == "downstream_rows":
            if expression != broker.WORKSHOP_EXACT_DESCRIPTION_EVALUATOR:
                raise AssertionError("unexpected production disclosure evaluator")
            return (
                self.count() == 5
                and self.page.store.fault
                not in {
                    "downstream_unavailable",
                    "downstream_nested_row",
                    "downstream_split_row",
                }
                and payload.get("term") == "Downstream use"
                and payload.get("description") == "Not used elsewhere"
            )
        if operation == "count":
            return self.count()
        if self.count() != 1:
            raise RuntimeError("Workshop target cardinality refused")
        if operation == "text":
            return self.text_content()
        if operation == "input_value":
            return self.input_value()
        if operation == "attribute":
            return self.get_attribute(payload["name"])
        raise AssertionError(f"unmodelled evaluator read: {operation}")

    def check(self):
        if self.kind not in {"classification", "confirm_delete"}:
            raise AssertionError(f"unmodelled check: {self.selector}")
        self.page.checked.add(self.selector)

    def click(self):
        if self.kind == "submit":
            return
        if self.kind == "save_confirm":
            self.page.save_current()
            return
        if self.kind == "button":
            self.page.click_button(self.text)
            return
        raise AssertionError(f"unmodelled click: {self.kind}")

    def input_value(self):
        if self.kind != "row_version":
            raise AssertionError("unmodelled input_value")
        key = self.page.store.selected_key(self.page.context.owner, self.page.url)
        if key is None:
            raise AssertionError("row version requested outside owned item")
        return self.page.store.row_version(key)

    def get_attribute(self, name):
        if self.kind == "saved_link" and name == "href" and self.page.saved_key:
            return f"/app/workshop?item={self.page.saved_key}"
        return None

    def locator(self, selector):
        if self.kind == "history":
            mapping = {
                ".wk-wording-history__count": "history_count",
                ".wk-wording-history__note": "history_note",
                ".wk-wording-history__window": "history_window",
                ".wk-wording-history__version": "history_versions",
            }
            return StrictLocator(self.page, mapping.get(selector, "unknown"))
        if self.kind == "history_row" and selector == ".wk-wording-history__wording":
            return StrictLocator(self.page, "history_wordings", row=self.row)
        if self.kind == "downstream_row" and selector == "dd":
            return StrictLocator(self.page, "downstream_dd")
        return StrictLocator(self.page)

    def get_by_text(self, text, *, exact):
        if self.kind == "history_row":
            return StrictLocator(
                self.page,
                "version_label",
                text=text,
                exact=exact,
                row=self.row,
            )
        return StrictLocator(self.page)

    def filter(self, *, has_text):
        if self.kind == "downstream_rows" and has_text == "Downstream use":
            return StrictLocator(self.page, "downstream_row")
        return StrictLocator(self.page)

    def nth(self, index):
        if self.kind == "history_versions":
            return StrictLocator(self.page, "history_row", row=index)
        if self.kind == "history_wordings":
            return StrictLocator(
                self.page, "history_wording", row=self.row, slot=index
            )
        return StrictLocator(self.page)

    def text_content(self):
        item = self._selected_item()
        if self.kind == "history_count":
            return f"{len(item['versions'])} retained" if item else ""
        if self.kind == "history_note":
            if self.page.store.fault == "history_note":
                return "unverified history note"
            return broker.WORKSHOP_HISTORY_NOTE
        if self.kind == "history_wording" and item is not None:
            rows = self._history_rows()
            if self.row is None or self.row >= len(rows):
                return ""
            if self.slot == 0:
                return rows[self.row]
            source = item["versions"][0]
            if self.page.store.fault == "source_changed":
                source += " altered"
            return source
        if self.kind == "downstream_dd":
            if self.page.store.fault == "downstream_unavailable":
                return "could not check just now"
            return "Not used elsewhere"
        return ""


class StrictContext:
    def __init__(self, store):
        self.store = store
        self.owner = None
        self.closed = False
        self.pages = []

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
        self.closed = False

    def goto(self, url, *, wait_until):
        if wait_until != "domcontentloaded":
            raise AssertionError("unexpected navigation wait")
        if "/.auth/login/" in url:
            self.url = f"{AUTHORIZATION_ORIGIN}/authorize"
        elif "/.auth/logout" in url:
            self.context.owner = None
            self.url = "https://peerslate.com/"
        else:
            self.url = url

    def assert_canonical_document(self, payload):
        parsed = urlparse(self.url)
        if (
            payload.get("expectedOrigin") != broker.ALLOWED_SITE_ORIGIN
            or parsed.scheme != "https"
            or parsed.netloc != "peerslate.com"
            or parsed.hostname != "peerslate.com"
            or parsed.port is not None
            or parsed.username is not None
            or parsed.password is not None
        ):
            raise RuntimeError("Workshop document refused")

    def evaluate(self, expression, payload):
        del expression
        self.assert_canonical_document(payload)
        return True

    def wait_for_url(self, pattern, *, timeout):
        if timeout != 60000 or not pattern.search("https://peerslate.com/app"):
            raise AssertionError("unexpected member arrival wait")
        login = self.fields.get(broker.IDENTITY_USERNAME_SELECTOR, "")
        if "-member_a@" in login:
            self.context.owner = "member_a"
        elif "-member_b@" in login:
            self.context.owner = "member_b"
        else:
            raise AssertionError("unexpected synthetic login")
        self.url = "https://peerslate.com/app"

    def locator(self, selector):
        mapping = {
            ".wk-status-banner--preview": "preview",
            broker.AUTHENTICATED_WORKSHOP_CONTROL: "authenticated",
            "input[name='expected_row_version']": "row_version",
            "#wk-title": "field",
            "#wk-wording": "field",
            "input[name='classification'][value='unclassified']": "classification",
            "button[name='save_action'][value='confirm']": "save_confirm",
            "input[name='confirm_delete']": "confirm_delete",
            broker.IDENTITY_USERNAME_SELECTOR: "username",
            "input[type='password']": "password",
            "input[type='submit']": "submit",
            "details.wk-wording-history": "history",
            ".wk-detail__meta-row": "downstream_rows",
            "article.wk-detail": "article_detail",
        }
        return StrictLocator(
            self, mapping.get(selector, "unknown"), selector=selector
        )

    def get_by_text(self, text, *, exact):
        deletion_texts = {
            "Permanent deletion",
            "could not check just now",
            "Your saved Opportunity Slate cites this item",
        }
        kind = "deletion_text" if text in deletion_texts else "marker_text"
        return StrictLocator(self, kind, text=text, exact=exact)

    def get_by_role(self, role, *, name):
        if role == "button":
            return StrictLocator(self, "button", text=name)
        if role == "link" and name == "View in My Information":
            return StrictLocator(self, "saved_link")
        return StrictLocator(self)

    def save_current(self):
        key = self.store.selected_key(self.context.owner, self.url)
        wording = self.fields.get("#wk-wording")
        if not isinstance(wording, str):
            raise AssertionError("missing wording")
        if key is None:
            marker = self.fields.get("#wk-title")
            key = self.store.create(self.context.owner, marker, wording)
        else:
            self.store.append_version(key, wording)
        self.saved_key = key
        self.url = f"https://peerslate.com/app/workshop/items/{key}/saved"

    def click_button(self, name):
        if name == "Continue":
            return
        key = self.store.selected_key(self.context.owner, self.url)
        if name == "Archive" and key:
            self.store.items[key]["status"] = "archived"
            self.store.bump_concurrency(key)
            return
        if name == "Restore" and key:
            self.store.items[key]["status"] = "active"
            if self.store.fault == "restore_appends_version":
                self.store.append_version(
                    key,
                    f"{self.store.items[key]['versions'][-1]}-restore-appended",
                )
            else:
                self.store.bump_concurrency(key)
            return
        if name == "Delete permanently" and key:
            if "input[name='confirm_delete']" not in self.checked:
                raise AssertionError("delete was not confirmed")
            alias = self.store.items[key]["owner"]
            self.store.delete_attempts.append(alias)
            if self.store.delete_fault == alias:
                raise RuntimeError("synthetic deletion failure")
            self.store.deleted_history_lengths.append(
                len(self.store.items[key]["versions"])
            )
            del self.store.items[key]
            self.url = "https://peerslate.com/app/workshop"
            return
        raise AssertionError(f"unmodelled button: {name}")

    def reload(self, *, wait_until):
        if wait_until != "domcontentloaded":
            raise AssertionError("unexpected reload wait")

    def close(self):
        self.closed = True


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


class StrictRuntime:
    expected_browser_version = "151.0.7922.34"

    def __init__(self):
        self.released = False

    def release(self):
        self.released = True


def identities():
    return broker._generate_identities(
        broker.SealedValue(ISSUER),
        run_id="qa-20260829-0001",
        choice=lambda _alphabet: "z",
    )


def complete_browser_outcome():
    observations = {
        journey_id: broker.JourneyObservation(
            status="pass",
            observed_outcome=journey.expected_outcome,
            note_code="none",
        )
        for journey_id, journey in JOURNEY_BY_ID.items()
    }
    for journey_id, note_code in broker.REQUIRED_CONDITIONAL_OUTCOMES.items():
        observations[journey_id] = broker.JourneyObservation(
            status="conditional",
            observed_outcome="limitation_recorded",
            note_code=note_code,
        )
    return broker.BrowserOutcome(
        journey_outcomes=observations,
        created_item_counts={"member_a": 1, "member_b": 1},
        edit_counts={"member_a": 2, "member_b": 2},
        retained_version_counts={"member_a": 3, "member_b": 3},
        retained_source_proof_counts={"member_a": 3, "member_b": 3},
        downstream_disclosure_counts={"member_a": 1, "member_b": 1},
        active_residue_counts={"member_a": 0, "member_b": 0},
        archived_residue_counts={"member_a": 0, "member_b": 0},
        clean_start_confirmed=True,
    )


def child_frame(payload):
    return (
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        + b"\n"
    )


def child_identity_payload(source_identities):
    return [
        {
            "alias": identity.alias,
            "login_identifier": identity.login_identifier.reveal(),
            "password": identity.password.reveal(),
            "mail_nickname": identity.mail_nickname.reveal(),
        }
        for identity in source_identities
    ]


class RecordingChildOutput(io.BytesIO):
    def __init__(self, events):
        super().__init__()
        self.events = events

    def write(self, data):
        payload = json.loads(bytes(data))
        self.events.append(
            "write_" + payload["type"] + "_" + str(payload.get("result", ""))
        )
        return super().write(data)


class FakeChildOwnedSession:
    def __init__(self, events, *, cleanup=None, outcome=None):
        self.events = events
        self.identities = ()
        self.cleanup = cleanup or broker.BrowserCleanup(4, False)
        self.outcome = outcome or complete_browser_outcome()

    def pre_graph_proof(self):
        self.events.append("child_preflight")
        return broker.BrowserPreflight(True, True, True, 4, True)

    def exercise_canonical_journeys(self, parsed_identities):
        self.events.append("child_journeys")
        self.identities = tuple(parsed_identities)
        return self.outcome

    def destroy_and_verify(self):
        self.events.append("child_cleanup")
        if isinstance(self.cleanup, Exception):
            raise self.cleanup
        return self.cleanup


class IsolatedChildWorkerTests(unittest.TestCase):
    def test_child_accepts_only_canonical_windows_and_interpreter_env_keys(self):
        with TemporaryDirectory() as outer:
            workspace = Path(outer) / f"{broker.BROWSER_TEMP_PREFIX}fake"
            system_root = Path(outer) / "trusted-windows"
            venv_python = workspace / "runtime" / "venv" / "Scripts" / "python.exe"
            site_packages = workspace / "runtime" / "venv" / "Lib" / "site-packages"
            browsers = workspace / "runtime" / "browsers"
            venv_python.parent.mkdir(parents=True)
            venv_python.write_text("fake", encoding="utf-8")
            site_packages.mkdir(parents=True)
            browsers.mkdir(parents=True)
            system_root.mkdir()
            environment = {
                name: str(workspace)
                for name in (
                    "HOME",
                    "USERPROFILE",
                    "APPDATA",
                    "LOCALAPPDATA",
                    "TEMP",
                    "TMP",
                    "TMPDIR",
                )
            }
            environment.update(
                {
                    "PLAYWRIGHT_BROWSERS_PATH": str(browsers),
                    "SYSTEMROOT": str(system_root),
                    "WINDIR": str(system_root),
                    # CPython may synthesize these keys from an otherwise
                    # scrubbed environment before child code runs.
                    "LC_CTYPE": "UTF-8",
                    "__CF_USER_TEXT_ENCODING": "0x1F5:0x0:0x0",
                }
            )
            lock = {
                "active_target": {
                    "venv_python": ["Scripts", "python.exe"],
                    "site_packages": ["Lib", "site-packages"],
                },
                "chromium": {"browser_version": "151.0.7922.34"},
            }
            with (
                patch.object(child_worker.os, "environ", environment),
                patch.object(child_worker.sys, "executable", str(venv_python)),
                patch.object(
                    child_worker.PinnedPlaywrightRuntime,
                    "_lock",
                    return_value=lock,
                ),
                patch.object(
                    broker,
                    "_canonical_windows_system_root",
                    return_value=system_root.resolve(),
                ),
            ):
                resolved_workspace, runtime = (
                    child_worker._native_child_runtime_provider()
                )

            self.assertEqual(resolved_workspace, workspace.resolve())
            self.assertEqual(runtime.expected_browser_version, "151.0.7922.34")
            self.assertNotIn("SystemRoot", environment)
            self.assertLessEqual(
                set(environment), broker.ALLOWED_BROWSER_CHILD_ENV_NAMES
            )

            environment["SYSTEMROOT"] = str(workspace)
            with (
                patch.object(child_worker.os, "environ", environment),
                patch.object(
                    broker,
                    "_canonical_windows_system_root",
                    return_value=system_root.resolve(),
                ),
                self.assertRaisesRegex(
                    broker.BrokerRefusal, "sealed_browser_environment_refused"
                ),
            ):
                child_worker._native_child_runtime_provider()

    def test_exact_two_identity_input_yields_structural_output_after_cleanup(self):
        events = []
        source_identities = identities()
        raw_identities = child_identity_payload(source_identities)
        secrets = [
            raw[key]
            for raw in raw_identities
            for key in ("login_identifier", "password", "mail_nickname")
        ]
        input_stream = io.BytesIO(
            child_frame(
                {
                    "schema_version": 1,
                    "type": "prepare",
                    "authorization_origin": AUTHORIZATION_ORIGIN,
                }
            )
            + child_frame(
                {
                    "schema_version": 1,
                    "type": "identities",
                    "identities": raw_identities,
                }
            )
        )
        output_stream = RecordingChildOutput(events)
        session = FakeChildOwnedSession(events)

        def session_factory(origin):
            events.append("child_session_prepare")
            self.assertEqual(origin.reveal(), AUTHORIZATION_ORIGIN)
            return session

        try:
            self.assertEqual(
                child_worker._browser_child_main(
                    input_stream,
                    output_stream,
                    session_factory=session_factory,
                ),
                0,
            )
        finally:
            for identity in source_identities:
                identity.clear()

        self.assertEqual(
            events,
            [
                "child_session_prepare",
                "child_preflight",
                "write_ready_",
                "child_journeys",
                "child_cleanup",
                "write_complete_ok",
            ],
        )
        frames = [
            json.loads(line) for line in output_stream.getvalue().splitlines()
        ]
        self.assertEqual([frame["type"] for frame in frames], ["ready", "complete"])
        self.assertEqual(frames[1]["result"], "ok")
        self.assertEqual(
            frames[1]["cleanup"], {"destroyed_contexts": 4, "complete": True}
        )
        output_text = output_stream.getvalue().decode("utf-8")
        for secret in secrets:
            self.assertNotIn(secret, output_text)
        for identity in session.identities:
            with self.assertRaisesRegex(broker.BrokerRefusal, "sealed_value_cleared"):
                identity.password.reveal()

    def test_abort_closes_child_resources_before_the_final_frame(self):
        events = []
        input_stream = io.BytesIO(
            child_frame(
                {
                    "schema_version": 1,
                    "type": "prepare",
                    "authorization_origin": AUTHORIZATION_ORIGIN,
                }
            )
            + child_frame({"schema_version": 1, "type": "abort"})
        )
        output_stream = RecordingChildOutput(events)
        session = FakeChildOwnedSession(events)

        self.assertEqual(
            child_worker._browser_child_main(
                input_stream,
                output_stream,
                session_factory=lambda _origin: session,
            ),
            0,
        )

        self.assertLess(events.index("child_cleanup"), events.index("write_complete_aborted"))
        final = json.loads(output_stream.getvalue().splitlines()[-1])
        self.assertEqual(
            final,
            {
                "schema_version": 1,
                "type": "complete",
                "result": "aborted",
                "cleanup": {"destroyed_contexts": 4, "complete": True},
            },
        )

    def test_identity_coherence_and_child_only_cleanup_semantics_fail_closed(self):
        source_identities = identities()
        try:
            raw_identities = child_identity_payload(source_identities)
        finally:
            for identity in source_identities:
                identity.clear()
        raw_identities[1]["login_identifier"] = raw_identities[1][
            "login_identifier"
        ].replace(raw_identities[1]["login_identifier"][5:21], "f" * 16)
        with self.assertRaisesRegex(
            broker.BrokerRefusal, "sealed_browser_protocol_refused"
        ):
            child_worker._parse_child_identities(
                raw_identities, tenant_label="synthetic-tenant"
            )

        events = []
        input_stream = io.BytesIO(
            child_frame(
                {
                    "schema_version": 1,
                    "type": "prepare",
                    "authorization_origin": AUTHORIZATION_ORIGIN,
                }
            )
            + child_frame({"schema_version": 1, "type": "abort"})
        )
        output_stream = RecordingChildOutput(events)
        session = FakeChildOwnedSession(
            events, cleanup=broker.BrowserCleanup(4, True)
        )
        self.assertEqual(
            child_worker._browser_child_main(
                input_stream,
                output_stream,
                session_factory=lambda _origin: session,
            ),
            0,
        )
        final = json.loads(output_stream.getvalue().splitlines()[-1])
        self.assertEqual(final["result"], "indeterminate")
        self.assertEqual(
            final["reason_code"], "sealed_browser_cleanup_indeterminate"
        )
        self.assertEqual(
            final["cleanup"], {"destroyed_contexts": 0, "complete": False}
        )

    def test_unvalidated_journey_material_never_reaches_child_stdout(self):
        sentinel = "SENTINEL_PRIVATE_VALUE"
        outcome = complete_browser_outcome()
        journey_outcomes = dict(outcome.journey_outcomes)
        journey_id = next(iter(journey_outcomes))
        journey_outcomes[journey_id] = broker.JourneyObservation(
            status="pass",
            observed_outcome=sentinel,
            note_code="none",
        )
        outcome = broker.BrowserOutcome(
            journey_outcomes=journey_outcomes,
            created_item_counts=outcome.created_item_counts,
            edit_counts=outcome.edit_counts,
            retained_version_counts=outcome.retained_version_counts,
            retained_source_proof_counts=outcome.retained_source_proof_counts,
            downstream_disclosure_counts=outcome.downstream_disclosure_counts,
            active_residue_counts=outcome.active_residue_counts,
            archived_residue_counts=outcome.archived_residue_counts,
            clean_start_confirmed=outcome.clean_start_confirmed,
        )
        source_identities = identities()
        try:
            raw_identities = child_identity_payload(source_identities)
        finally:
            for identity in source_identities:
                identity.clear()
        input_stream = io.BytesIO(
            child_frame(
                {
                    "schema_version": 1,
                    "type": "prepare",
                    "authorization_origin": AUTHORIZATION_ORIGIN,
                }
            )
            + child_frame(
                {
                    "schema_version": 1,
                    "type": "identities",
                    "identities": raw_identities,
                }
            )
        )
        output_stream = RecordingChildOutput([])
        session = FakeChildOwnedSession([], outcome=outcome)

        self.assertEqual(
            child_worker._browser_child_main(
                input_stream,
                output_stream,
                session_factory=lambda _origin: session,
            ),
            0,
        )

        output_text = output_stream.getvalue().decode("utf-8")
        self.assertNotIn(sentinel, output_text)
        final = json.loads(output_stream.getvalue().splitlines()[-1])
        self.assertEqual(final["result"], "indeterminate")
        self.assertEqual(
            final["reason_code"], "sealed_browser_operation_indeterminate"
        )


class AttendedJourneyTests(unittest.TestCase):
    def session(self, outer, *, store=None):
        store = store or StrictWorkshopStore()
        contexts = {
            name: StrictContext(store)
            for name in ("member_a", "member_b", "signed_out", "switch")
        }
        browser = StrictBrowser()
        playwright = StrictPlaywright()
        runtime = StrictRuntime()
        workspace = Path(outer) / "operation"
        workspace.mkdir()
        adapter = broker.PlaywrightBrowserAdapter(
            environment={}, workspace_root=Path(outer)
        )
        attended = broker._PlaywrightAttendedSession(
            adapter=adapter,
            contexts=contexts,
            browser=browser,
            playwright=playwright,
            runtime_provider=runtime,
            workspace=workspace,
            authorization_origin=broker.SealedValue(AUTHORIZATION_ORIGIN),
            signed_out_page=contexts["signed_out"].new_page(),
            preflight=broker.BrowserPreflight(True, True, True, 4, True),
            preflight_outcomes={
                journey_id: broker._pass_observation(journey_id)
                for journey_id in (
                    "clean_client_a_start",
                    "clean_client_b_start",
                    "clean_signed_out_control_start",
                    "signed_out_private_baseline",
                )
            },
        )
        return store, contexts, browser, playwright, runtime, workspace, attended

    def test_exact_journeys_history_disclosure_and_zero_residue(self):
        with TemporaryDirectory() as outer:
            (
                store,
                contexts,
                browser,
                playwright,
                runtime,
                workspace,
                attended,
            ) = self.session(outer)
            self.assertEqual(
                attended.pre_graph_proof(),
                broker.BrowserPreflight(True, True, True, 4, True),
            )

            outcome = attended.exercise_canonical_journeys(identities())

            self.assertEqual(set(outcome.journey_outcomes), set(JOURNEY_BY_ID))
            self.assertEqual(
                {
                    journey_id: observation.note_code
                    for journey_id, observation in outcome.journey_outcomes.items()
                    if observation.status == "conditional"
                },
                broker.REQUIRED_CONDITIONAL_OUTCOMES,
            )
            self.assertEqual(outcome.edit_counts, {"member_a": 2, "member_b": 2})
            self.assertEqual(
                outcome.retained_version_counts,
                {"member_a": 3, "member_b": 3},
            )
            self.assertEqual(
                outcome.retained_source_proof_counts,
                {"member_a": 3, "member_b": 3},
            )
            self.assertEqual(
                outcome.downstream_disclosure_counts,
                {"member_a": 1, "member_b": 1},
            )
            self.assertEqual(outcome.active_residue_counts, {"member_a": 0, "member_b": 0})
            self.assertEqual(outcome.archived_residue_counts, {"member_a": 0, "member_b": 0})
            self.assertEqual(store.items, {})
            self.assertEqual(store.version_appends, 4)
            self.assertEqual(store.concurrency_only_bumps, 4)
            self.assertEqual(store.deleted_history_lengths, [3, 3])
            self.assertEqual(store.delete_attempts, ["member_a", "member_b"])
            # An unmodelled selector cannot false-pass a newly added proof.
            self.assertEqual(contexts["member_a"].pages[0].locator(".unknown").count(), 0)

            cleanup = attended.destroy_and_verify()
            self.assertEqual(cleanup, broker.BrowserCleanup(4, True))
            self.assertFalse(workspace.exists())
            self.assertTrue(all(context.closed for context in contexts.values()))
            self.assertTrue(browser.closed and playwright.stopped and runtime.released)

    def test_history_and_downstream_tampering_fail_and_still_delete_both_items_once(self):
        for fault in (
            "history_order",
            "source_changed",
            "history_window",
            "missing_version",
            "history_note",
            "downstream_unavailable",
            "downstream_nested_row",
            "downstream_split_row",
        ):
            with self.subTest(fault=fault), TemporaryDirectory() as outer:
                store = StrictWorkshopStore(fault=fault)
                *_, workspace, attended = self.session(outer, store=store)
                with self.assertRaisesRegex(
                    broker.BrokerIndeterminate,
                    "sealed_browser_operation_indeterminate",
                ):
                    attended.exercise_canonical_journeys(identities())
                self.assertEqual(store.items, {})
                self.assertEqual(store.delete_attempts, ["member_a", "member_b"])
                attended.destroy_and_verify()
                self.assertFalse(workspace.exists())

    def test_restore_appended_fourth_version_is_rejected_and_cleaned(self):
        with TemporaryDirectory() as outer:
            store = StrictWorkshopStore(fault="restore_appends_version")
            *_, workspace, attended = self.session(outer, store=store)
            with self.assertRaisesRegex(
                broker.BrokerIndeterminate,
                "sealed_browser_operation_indeterminate",
            ):
                attended.exercise_canonical_journeys(identities())
            self.assertEqual(store.items, {})
            self.assertEqual(store.delete_attempts, ["member_a", "member_b"])
            self.assertEqual(store.deleted_history_lengths, [4, 4])
            attended.destroy_and_verify()
            self.assertFalse(workspace.exists())

    def test_one_item_cleanup_failure_does_not_skip_the_other_item(self):
        with TemporaryDirectory() as outer:
            store = StrictWorkshopStore(
                fault="source_changed", delete_fault="member_a"
            )
            *_, attended = self.session(outer, store=store)
            with self.assertRaises(broker.BrokerIndeterminate):
                attended.exercise_canonical_journeys(identities())
            self.assertEqual(store.delete_attempts, ["member_a", "member_b"])
            self.assertEqual(
                {item["owner"] for item in store.items.values()}, {"member_a"}
            )
            attended.destroy_and_verify()

    def test_foreign_checks_are_conditionals_without_a_mutation_api(self):
        with TemporaryDirectory() as outer:
            store, contexts, *_, attended = self.session(outer)
            self.assertFalse(hasattr(contexts["member_a"], "request"))
            outcome = attended.exercise_canonical_journeys(identities())
            self.assertEqual(
                {
                    journey_id: observation.note_code
                    for journey_id, observation in outcome.journey_outcomes.items()
                    if observation.status == "conditional"
                },
                broker.REQUIRED_CONDITIONAL_OUTCOMES,
            )
            self.assertEqual(store.items, {})
            self.assertEqual(store.delete_attempts, ["member_a", "member_b"])
            attended.destroy_and_verify()


if __name__ == "__main__":
    unittest.main()

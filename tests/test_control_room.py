"""Guardrails for the owner-only, read-only PeerSlate Control Room.

Coverage:
* Authorization — unauthenticated and authenticated non-owners are refused; the
  configured owner is admitted; client-supplied fields cannot elevate; the data
  endpoint is protected independently of the page; fail-closed when unconfigured.
* Read-only — only GET routes exist, and the projection layer never touches the
  database service.
* Source truthfulness — missing sources render unavailable/unknown, live delivery
  integration is never claimed green, and traceability is labelled partial.
* Non-exposure — the route is absent from the sitemap and public navigation, and
  owner responses carry noindex + no-store headers.
"""

import base64
import importlib.util
import inspect
import json
import os
import unittest
from unittest.mock import patch

from app import app
import control_room_projection as projection


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _load_snapshot_generator():
    """Load scripts/generate_control_room_snapshot.py without requiring the
    scripts/ directory to be an importable package."""
    path = os.path.join(ROOT, "scripts", "generate_control_room_snapshot.py")
    spec = importlib.util.spec_from_file_location(
        "generate_control_room_snapshot", path
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SNAPSHOT_GENERATOR = _load_snapshot_generator()


def _snapshot_fixture(**overrides):
    fixture = {
        "schema_version": 1,
        "generated_at": "2026-07-19T18:20:00Z",
        "build": {
            "id": "112",
            "source_version": "fd27b2147b6a34019353d038331f4bde4f97d3b5",
            "source_branch": "refs/heads/main",
        },
        "commits": [
            {
                "commit": "fd27b21",
                "full": "fd27b2147b6a34019353d038331f4bde4f97d3b5",
                "date": "2026-07-19",
                "author": "Pete Carter",
                "subject": "Merge pull request 74 into main",
            }
        ],
    }
    fixture.update(overrides)
    return fixture

PAGE = "/owner/control-room"
DATA = "/owner/control-room/data.json"

OWNER_EMAIL = "owner@example.com"
NON_OWNER_EMAIL = "stranger@example.com"

# A dashboard fingerprint that must never appear in a refused response.
LEAK_MARKERS = (b"Project state at a glance", b"Control Room", b"PS-VOICE-001")


def easy_auth_header(subject, email, display_name="Example Member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": display_name},
            {"typ": "email", "val": email},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


def _db_row(email, user_key="member-key-123"):
    return {
        "account_key": user_key,
        "user_key": user_key,
        "display_name": "Example Member",
        "email": email,
    }


class ControlRoomAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self._saved = {
            key: app.config.get(key)
            for key in (
                "TESTING",
                "PEERSLATE_ALLOW_DEV_IDENTITY",
                "PEERSLATE_DEV_USER_KEY",
                "PEERSLATE_TRUST_EASYAUTH_HEADERS",
                "PEERSLATE_AUTH_ISSUER",
                "PEERSLATE_OWNER_EMAILS",
                "PEERSLATE_OWNER_USER_KEYS",
            )
        }
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_AUTH_ISSUER=None,
            PEERSLATE_OWNER_EMAILS=OWNER_EMAIL,
            PEERSLATE_OWNER_USER_KEYS="",
        )
        self.client = app.test_client()

    def tearDown(self):
        app.config.update(self._saved)

    # --- unauthenticated --------------------------------------------------
    def test_unauthenticated_page_is_not_found(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = False
        response = self.client.get(PAGE)
        self.assertEqual(response.status_code, 404)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, response.data)

    def test_unauthenticated_data_endpoint_is_not_found(self):
        app.config["PEERSLATE_TRUST_EASYAUTH_HEADERS"] = False
        response = self.client.get(DATA)
        self.assertEqual(response.status_code, 404)

    # --- authenticated non-owner -----------------------------------------
    @patch("identity.database_service.first_row")
    def test_authenticated_non_owner_page_is_not_found(self, first_row):
        first_row.return_value = _db_row(NON_OWNER_EMAIL)
        response = self.client.get(
            PAGE, headers=easy_auth_header("stranger-id", NON_OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 404)
        for marker in LEAK_MARKERS:
            self.assertNotIn(marker, response.data)

    @patch("identity.database_service.first_row")
    def test_authenticated_non_owner_data_endpoint_is_not_found(self, first_row):
        first_row.return_value = _db_row(NON_OWNER_EMAIL)
        response = self.client.get(
            DATA, headers=easy_auth_header("stranger-id", NON_OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 404)

    @patch("identity.database_service.first_row")
    def test_unmapped_principal_has_the_exact_neutral_denial_contract(
        self, first_row
    ):
        """A valid provider principal without an account cannot reveal either route.

        Compare against the existing mapped non-owner denial so both HTML and
        the data endpoint retain the same status, media type, and generic body.
        """
        headers = easy_auth_header("unmapped-id", NON_OWNER_EMAIL)

        for path in (PAGE, DATA):
            with self.subTest(path=path):
                first_row.return_value = _db_row(NON_OWNER_EMAIL)
                ordinary_denial = self.client.get(path, headers=headers)
                first_row.return_value = None
                unmapped_denial = self.client.get(path, headers=headers)

                self.assertEqual(ordinary_denial.status_code, 404)
                self.assertEqual(unmapped_denial.status_code, 404)
                self.assertEqual(
                    unmapped_denial.content_type, ordinary_denial.content_type
                )
                self.assertEqual(unmapped_denial.data, ordinary_denial.data)
                self.assertNotEqual(unmapped_denial.mimetype, "application/json")
                for marker in LEAK_MARKERS:
                    self.assertNotIn(marker, unmapped_denial.data)

        self.assertEqual(first_row.call_count, 4)

    # --- the owner --------------------------------------------------------
    @patch("identity.database_service.first_row")
    def test_owner_by_email_sees_the_dashboard(self, first_row):
        first_row.return_value = _db_row(OWNER_EMAIL)
        response = self.client.get(
            PAGE, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project state at a glance", response.data)
        self.assertIn(b"Read-only", response.data)

    @patch("identity.database_service.first_row")
    def test_owner_by_user_key_sees_the_dashboard(self, first_row):
        app.config["PEERSLATE_OWNER_EMAILS"] = ""
        app.config["PEERSLATE_OWNER_USER_KEYS"] = "vip-key-999"
        first_row.return_value = _db_row(NON_OWNER_EMAIL, user_key="vip-key-999")
        response = self.client.get(
            PAGE, headers=easy_auth_header("owner-id", NON_OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Project state at a glance", response.data)

    @patch("identity.database_service.first_row")
    def test_owner_page_includes_detail_modal_and_store(self, first_row):
        first_row.return_value = _db_row(OWNER_EMAIL)
        response = self.client.get(
            PAGE, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 200)
        body = response.data
        # The dialog shell, a row button, and a per-initiative detail block.
        self.assertIn(b'id="cr-modal"', body)
        self.assertIn(b'role="dialog"', body)
        self.assertIn(b'class="cr-rowbtn"', body)
        self.assertIn(b'id="cr-detail-PS-VOICE-001"', body)
        # Real source content is present in the rendered detail (Outcome text).
        self.assertIn(b"owner-scoped Voice Capture", body)

    @patch("identity.database_service.first_row")
    def test_owner_data_endpoint_returns_json_projection(self, first_row):
        first_row.return_value = _db_row(OWNER_EMAIL)
        response = self.client.get(
            DATA, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["read_only"])
        self.assertIn("governance", payload)
        self.assertIn("generated_at", payload)

    # --- elevation attempts ----------------------------------------------
    @patch("identity.database_service.first_row")
    def test_client_supplied_fields_cannot_elevate(self, first_row):
        first_row.return_value = _db_row(NON_OWNER_EMAIL)
        headers = easy_auth_header("stranger-id", NON_OWNER_EMAIL)
        headers["X-Owner"] = "true"
        headers["X-Owner-Email"] = OWNER_EMAIL
        response = self.client.get(
            PAGE + "?owner=1&is_owner=true&role=owner", headers=headers
        )
        self.assertEqual(response.status_code, 404)

    # --- fail closed ------------------------------------------------------
    @patch("identity.database_service.first_row")
    def test_empty_allowlist_locks_everyone_out(self, first_row):
        app.config["PEERSLATE_OWNER_EMAILS"] = ""
        app.config["PEERSLATE_OWNER_USER_KEYS"] = ""
        first_row.return_value = _db_row(OWNER_EMAIL)
        response = self.client.get(
            PAGE, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertEqual(response.status_code, 404)

    # --- defense-in-depth headers ----------------------------------------
    @patch("identity.database_service.first_row")
    def test_owner_responses_are_noindex_and_non_cacheable(self, first_row):
        first_row.return_value = _db_row(OWNER_EMAIL)
        # The HTML page carries noindex and the site-wide non-cacheable policy.
        page = self.client.get(
            PAGE, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertIn("noindex", page.headers.get("X-Robots-Tag", ""))
        page_cache = page.headers.get("Cache-Control", "")
        self.assertTrue(
            "no-store" in page_cache or "no-cache" in page_cache, page_cache
        )
        # The JSON data endpoint keeps the stronger private/no-store policy.
        data = self.client.get(
            DATA, headers=easy_auth_header("owner-id", OWNER_EMAIL)
        )
        self.assertIn("noindex", data.headers.get("X-Robots-Tag", ""))
        self.assertIn("no-store", data.headers.get("Cache-Control", ""))


class ControlRoomReadOnlyTests(unittest.TestCase):
    def test_only_get_methods_are_registered(self):
        write_methods = {"POST", "PUT", "PATCH", "DELETE"}
        for rule in app.url_map.iter_rules():
            if rule.rule.startswith("/owner/control-room"):
                self.assertEqual(
                    write_methods & rule.methods,
                    set(),
                    f"{rule.rule} exposes a write method: {rule.methods}",
                )

    def test_projection_never_touches_the_database_service(self):
        source = inspect.getsource(projection)
        self.assertNotIn("database_service", source)
        self.assertNotIn("execute_procedure", source)

    def test_projection_declares_itself_read_only(self):
        built = projection.build_projection()
        self.assertTrue(built["read_only"])


class ControlRoomTruthfulnessTests(unittest.TestCase):
    def test_portable_manager_schema_has_a_human_label(self):
        baseline = {
            "manager": {
                "role": "package_designated_session_manager",
                "eligible_tools": "ChatGPT Work/Codex or Claude Co-Work",
                "current_assignments": "Codex reviews the active package",
            }
        }
        source = {"status": projection.OK, "path": "CURRENT_BASELINE.yaml"}
        with patch.object(projection, "_baseline", return_value=(baseline, source)):
            summary = projection.governance_summary()
        self.assertEqual(
            summary["manager"]["label"],
            "Package-designated session manager",
        )
        self.assertEqual(
            summary["manager"]["current_assignments"],
            "Codex reviews the active package",
        )

    def test_missing_source_renders_unavailable_not_favourable(self):
        with patch.object(projection, "_read", return_value=None):
            summary = projection.governance_summary()
        self.assertEqual(summary["status"], projection.UNAVAILABLE)

    def test_delivery_never_claims_live_green(self):
        delivery = projection.delivery_health()
        self.assertEqual(delivery["live_integration"], projection.UNAVAILABLE)
        self.assertIn("not configured", delivery["live_integration_note"].lower())

    def test_traceability_is_labelled_partial(self):
        trace = projection.traceability()
        self.assertTrue(trace["partial"])
        self.assertIn("partial", trace["note"].lower())

    def test_documents_flag_missing_files_as_unavailable(self):
        register = projection.documents_register()
        # Every catalogued row must carry an explicit status; a file that does
        # not exist must be 'unavailable', never silently 'ok'.
        for row in register["records"]:
            self.assertIn(
                row["status"],
                {projection.OK, projection.UNAVAILABLE, projection.UNKNOWN},
            )

    def test_yaml_subset_reader_parses_lists_and_nested_maps(self):
        data = projection.parse_yaml_subset(
            "top: value\n"
            "nested:\n"
            "  child: 1\n"
            "items:\n"
            "  - alpha\n"
            "  - beta\n"
            "packages:\n"
            "  - id: PS-X\n"
            "    owner: someone\n"
        )
        self.assertEqual(data["top"], "value")
        self.assertEqual(data["nested"]["child"], "1")
        self.assertEqual(data["items"], ["alpha", "beta"])
        self.assertEqual(data["packages"][0]["id"], "PS-X")
        self.assertEqual(data["packages"][0]["owner"], "someone")


class ControlRoomNonExposureTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_route_absent_from_public_sitemap(self):
        response = self.client.get("/sitemap.xml")
        self.assertEqual(response.status_code, 200)
        self.assertNotIn(b"control-room", response.data)
        self.assertNotIn(b"/owner/", response.data)

    def test_route_absent_from_public_navigation_template(self):
        base_path = os.path.join(ROOT, "templates", "base.html")
        with open(base_path, "r", encoding="utf-8", errors="ignore") as handle:
            base_html = handle.read()
        self.assertNotIn("control-room", base_html)
        self.assertNotIn("/owner/", base_html)

    def test_snapshot_file_is_not_publicly_reachable(self):
        response = self.client.get("/control_room_snapshot.json")
        self.assertEqual(response.status_code, 404)


class ControlRoomSnapshotTests(unittest.TestCase):
    """Tier 0: the build-time snapshot generator and its consumers."""

    # --- generator ----------------------------------------------------
    def test_generator_produces_valid_schema_from_real_git(self):
        snapshot = SNAPSHOT_GENERATOR.build_snapshot()
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertIn("generated_at", snapshot)
        self.assertIn("build", snapshot)
        self.assertIn("id", snapshot["build"])
        self.assertIn("source_version", snapshot["build"])
        self.assertIn("source_branch", snapshot["build"])
        # This repository has real git history, so commits should populate.
        self.assertIn("commits", snapshot)
        self.assertGreater(len(snapshot["commits"]), 0)
        first = snapshot["commits"][0]
        for key in ("commit", "full", "date", "author", "subject"):
            self.assertIn(key, first)
        self.assertEqual(len(first["full"]), 40)

    def test_generator_never_raises_when_git_missing(self):
        with patch.object(
            SNAPSHOT_GENERATOR.subprocess,
            "run",
            side_effect=OSError("git not found"),
        ):
            snapshot = SNAPSHOT_GENERATOR.build_snapshot()
        self.assertEqual(snapshot["schema_version"], 1)
        self.assertIn("build", snapshot)
        self.assertNotIn("commits", snapshot)

    def test_generator_main_never_raises_and_exits_zero(self):
        with patch.object(
            SNAPSHOT_GENERATOR, "SNAPSHOT_PATH", "/nonexistent/dir/out.json"
        ):
            # An unwritable path must not raise or propagate a nonzero exit;
            # the pipeline step must never fail the build over this file.
            exit_code = SNAPSHOT_GENERATOR.main()
        self.assertEqual(exit_code, 0)

    # --- recent_changes tiering -----------------------------------------
    def test_recent_changes_prefers_live_git_in_dev(self):
        result = projection.recent_changes()
        self.assertEqual(result["tier"], "live_git")
        self.assertEqual(result["status"], projection.OK)

    def test_recent_changes_falls_back_to_snapshot_when_git_unavailable(self):
        with patch.object(
            projection.subprocess, "run", side_effect=OSError("no git")
        ), patch.object(
            projection, "_read_snapshot", return_value=_snapshot_fixture()
        ):
            result = projection.recent_changes()
        self.assertEqual(result["tier"], "build_snapshot")
        self.assertEqual(result["status"], projection.OK)
        self.assertEqual(result["records"][0]["commit"], "fd27b21")
        self.assertIsNone(result["source"]["link"])

    def test_recent_changes_unavailable_when_neither_source_exists(self):
        with patch.object(
            projection.subprocess, "run", side_effect=OSError("no git")
        ), patch.object(projection, "_read_snapshot", return_value=None):
            result = projection.recent_changes()
        self.assertEqual(result["status"], projection.UNAVAILABLE)
        self.assertIsNone(result["tier"])
        self.assertEqual(result["records"], [])

    # --- build_identity ---------------------------------------------------
    def test_build_identity_reads_snapshot_when_present(self):
        with patch.object(
            projection, "_read_snapshot", return_value=_snapshot_fixture()
        ):
            identity = projection.build_identity()
        self.assertEqual(identity["status"], projection.OK)
        self.assertEqual(identity["environment"], "production_build")
        self.assertEqual(identity["build_id"], "112")
        self.assertEqual(identity["commit"], "fd27b21")
        self.assertEqual(
            identity["commit_full"],
            "fd27b2147b6a34019353d038331f4bde4f97d3b5",
        )
        self.assertEqual(identity["source_branch"], "refs/heads/main")

    def test_build_identity_reports_local_development_without_snapshot(self):
        with patch.object(projection, "_read_snapshot", return_value=None):
            identity = projection.build_identity()
        self.assertEqual(identity["status"], projection.OK)
        self.assertEqual(identity["environment"], "local_development")
        self.assertIsNone(identity["build_id"])
        self.assertIsNotNone(identity["commit_full"])

    def test_build_identity_unavailable_when_nothing_resolves(self):
        with patch.object(
            projection, "_read_snapshot", return_value=None
        ), patch.object(
            projection.subprocess, "run", side_effect=OSError("no git")
        ):
            identity = projection.build_identity()
        self.assertEqual(identity["status"], projection.UNAVAILABLE)
        self.assertEqual(identity["environment"], "unknown")

    # --- malformed snapshot never raises -----------------------------------
    def test_malformed_snapshot_json_is_treated_as_absent(self):
        with patch.object(
            projection, "_read", return_value="{not valid json"
        ):
            self.assertIsNone(projection._read_snapshot())

    def test_snapshot_missing_schema_version_is_treated_as_absent(self):
        with patch.object(
            projection, "_read", return_value=json.dumps({"build": {}})
        ):
            self.assertIsNone(projection._read_snapshot())


SAMPLE_README = """# PS-EXAMPLE-001 - Example Initiative

## Assignment

- Writer: Someone
- Entry gate: after the prior thing

## Outcome

Do the useful thing in a **clear** way.

record -> review -> save

## Acceptance criteria

1. First criterion holds.
2. Second criterion holds.

## Writable files

- `some/path.py`
- `another/path.py`

## Required reading

Follow `START_HERE.md` and the baseline.
"""


class ControlRoomInitiativeDetailTests(unittest.TestCase):
    """The initiative pop-out detail parser and provider."""

    def test_detail_parser_lifts_outcome_as_summary(self):
        detail = projection._parse_initiative_detail(SAMPLE_README)
        self.assertIsNotNone(detail)
        summary_text = " ".join(
            b["text"] for b in detail["summary_blocks"] if b["type"] == "paragraph"
        )
        self.assertIn("useful thing", summary_text)
        # Emphasis markers are stripped for readable display.
        self.assertNotIn("**", summary_text)

    def test_detail_parser_keeps_meaningful_sections(self):
        detail = projection._parse_initiative_detail(SAMPLE_README)
        headings = [s["heading"] for s in detail["sections"]]
        self.assertIn("Acceptance criteria", headings)
        self.assertIn("Assignment", headings)
        # A numbered list is parsed as an ordered list of items.
        crit = next(s for s in detail["sections"] if s["heading"] == "Acceptance criteria")
        crit_list = next(b for b in crit["blocks"] if b["type"] == "list")
        self.assertTrue(crit_list["ordered"])
        self.assertEqual(len(crit_list["items"]), 2)

    def test_detail_parser_skips_plumbing_sections(self):
        detail = projection._parse_initiative_detail(SAMPLE_README)
        headings = [s["heading"].lower() for s in detail["sections"]]
        self.assertNotIn("writable files", headings)
        self.assertNotIn("required reading", headings)

    def test_detail_parser_returns_none_without_readme(self):
        self.assertIsNone(projection._parse_initiative_detail(None))
        self.assertIsNone(projection._parse_initiative_detail(""))

    def test_initiative_details_covers_real_packages(self):
        details = projection.initiative_details()
        self.assertIn("PS-VOICE-001", details)
        voice = details["PS-VOICE-001"]
        self.assertTrue(voice["has_readme"])
        self.assertTrue(len(voice["summary_blocks"]) > 0)
        self.assertTrue(len(voice["sections"]) > 0)

    def test_initiative_details_missing_readme_is_graceful(self):
        # A directory without a README must not raise and must report empty.
        details = projection.initiative_details()
        for record in details.values():
            self.assertIn("has_readme", record)
            if not record["has_readme"]:
                self.assertEqual(record["summary_blocks"], [])
                self.assertEqual(record["sections"], [])

    def test_detail_is_not_in_the_lean_json_projection(self):
        # Detail is page-only; the polled data.json must stay lean.
        serialized = json.dumps(projection.build_projection())
        self.assertNotIn("summary_blocks", serialized)


class ControlRoomDriftTests(unittest.TestCase):
    """Tier0 (deployed commit) x Tier1 (live main tip) deployment drift."""

    def _activity(self, main_commit_full, commits_main):
        return {
            "status": projection.OK,
            "branches": {
                "status": projection.OK,
                "items": [{"name": "main", "commit_full": main_commit_full}],
            },
            "commits_main": {"status": projection.OK, "items": commits_main},
        }

    def test_equal_shas_is_up_to_date(self):
        sha = "a" * 40
        build = {"commit_full": sha}
        activity = self._activity(sha, [{"commit_full": sha}])
        drift = projection._compute_drift(build, activity)
        self.assertEqual(drift["state"], "up_to_date")
        self.assertEqual(drift["pending_commits"], [])

    def test_deployed_sha_behind_tip_counts_pending_commits(self):
        deployed = "c" * 40
        commits = [
            {"commit_full": "e" * 40, "subject": "newest"},
            {"commit_full": "d" * 40, "subject": "middle"},
            {"commit_full": deployed, "subject": "deployed one"},
            {"commit_full": "b" * 40, "subject": "older"},
        ]
        build = {"commit_full": deployed}
        activity = self._activity("e" * 40, commits)
        drift = projection._compute_drift(build, activity)
        self.assertEqual(drift["state"], "behind")
        self.assertEqual(len(drift["pending_commits"]), 2)
        self.assertIn("2 commit(s)", drift["detail"])

    def test_missing_build_commit_is_unknown(self):
        activity = self._activity("e" * 40, [{"commit_full": "e" * 40}])
        drift = projection._compute_drift({"commit_full": None}, activity)
        self.assertEqual(drift["state"], "unknown")

    def test_missing_main_tip_is_unknown(self):
        build = {"commit_full": "a" * 40}
        activity = {
            "status": projection.UNAVAILABLE,
            "branches": {"status": projection.UNAVAILABLE, "items": []},
            "commits_main": {"status": projection.UNAVAILABLE, "items": []},
        }
        drift = projection._compute_drift(build, activity)
        self.assertEqual(drift["state"], "unknown")

    def test_deployed_sha_not_in_fetched_window_is_unknown_not_a_guess(self):
        # The deployed commit is real but older than the fetched history
        # window (e.g. a shallow/limited commit list) — must not be guessed
        # as "behind" without evidence.
        build = {"commit_full": "f" * 40}
        activity = self._activity("e" * 40, [{"commit_full": "e" * 40}])
        drift = projection._compute_drift(build, activity)
        self.assertEqual(drift["state"], "unknown")


class ControlRoomRepositoryActivityTests(unittest.TestCase):
    """The projection-layer wiring around Tier 1 (config injection, overview
    warnings) — endpoint-level behavior is covered by
    tests/test_azure_devops_read.py."""

    def setUp(self):
        import services.azure_devops_read as ado
        self.ado = ado
        ado.reset_cache()

    def test_not_configured_surfaces_as_an_overview_warning(self):
        proj = projection.build_projection(app_config={})
        self.assertEqual(
            proj["repository_activity"]["status"], "not_configured"
        )
        subjects = [w["subject"] for w in proj["overview"]["warnings"]]
        self.assertIn("Repository activity", subjects)

    def test_build_projection_without_app_config_does_not_raise(self):
        # No Flask app/request context and no app_config passed: must degrade
        # to "not configured" rather than raising RuntimeError.
        proj = projection.build_projection()
        self.assertEqual(
            proj["repository_activity"]["status"], "not_configured"
        )

    def test_configured_and_reachable_is_ok_with_no_warning(self):
        from unittest.mock import patch
        import tests.test_azure_devops_read as ado_fixtures

        full_config = dict(ado_fixtures.FULL_CONFIG)
        with patch(
            "urllib.request.urlopen",
            side_effect=ado_fixtures._success_side_effect,
        ):
            proj = projection.build_projection(app_config=full_config)
        self.assertEqual(proj["repository_activity"]["status"], projection.OK)
        subjects = [w["subject"] for w in proj["overview"]["warnings"]]
        self.assertNotIn("Repository activity", subjects)


if __name__ == "__main__":
    unittest.main()

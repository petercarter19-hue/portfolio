"""Flask wiring tests for the private My Data entrance.

Gate behavior, member isolation, truthful unavailable states, and the
bootstrap contract. Mutations ride the accepted entry-policy and intake
APIs; these tests prove the entrance exposes them without leaking data
across members or when the gate is off. No live database or provider.
"""

import base64
import json
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4

from app import app
from services.entry_policy_repository import InMemoryEntryPolicyRepository
from services.entry_policy_service import EntryPolicyService
from services.resume_guide_service import ResumeGuideService
from services.resume_intake_policy import MY_DATA_POLICY
from services.resume_intake_repository import InMemoryResumeIntakeRepository
from services.resume_intake_service import ResumeIntakeService


def key(n):
    return str(UUID(int=n, version=4))


def easy_auth_header(subject, display_name="Example Member"):
    principal = {
        "auth_typ": "aad",
        "claims": [
            {"typ": "iss", "val": "https://example.ciamlogin.com/example/v2.0/"},
            {"typ": "oid", "val": subject},
            {"typ": "name", "val": display_name},
            {"typ": "email", "val": f"{subject}@example.com"},
        ],
    }
    encoded = base64.b64encode(json.dumps(principal).encode("utf-8")).decode("ascii")
    return {"X-MS-CLIENT-PRINCIPAL": encoded}


CONFIG_KEYS = (
    "TESTING",
    "PEERSLATE_ALLOW_DEV_IDENTITY",
    "PEERSLATE_DEV_USER_KEY",
    "PEERSLATE_TRUST_EASYAUTH_HEADERS",
    "PEERSLATE_MY_DATA_ENABLED",
    "PEERSLATE_ENTRY_POLICY_ENABLED",
    "PEERSLATE_RESUME_INTAKE_ENABLED",
    "ENTRY_POLICY_SERVICE",
    "RESUME_INTAKE_SERVICE",
    "RESUME_GUIDE_SERVICE",
)


class MyDataRouteTests(unittest.TestCase):
    def setUp(self):
        self.original = {name: app.config.get(name) for name in CONFIG_KEYS}
        self.entries = EntryPolicyService(repository=InMemoryEntryPolicyRepository())
        repository = InMemoryResumeIntakeRepository()
        self.intake = ResumeIntakeService(repository=repository, policy=MY_DATA_POLICY)
        app.config.update(
            TESTING=True,
            PEERSLATE_ALLOW_DEV_IDENTITY=False,
            PEERSLATE_DEV_USER_KEY=None,
            PEERSLATE_TRUST_EASYAUTH_HEADERS=True,
            PEERSLATE_MY_DATA_ENABLED=True,
            PEERSLATE_ENTRY_POLICY_ENABLED=True,
            PEERSLATE_RESUME_INTAKE_ENABLED=True,
            ENTRY_POLICY_SERVICE=self.entries,
            RESUME_INTAKE_SERVICE=self.intake,
            RESUME_GUIDE_SERVICE=ResumeGuideService(repository=repository),
        )
        self.client = app.test_client()
        self._identity_patch = patch("identity.database_service.first_row")
        self.first_row = self._identity_patch.start()
        self.first_row.return_value = {
            "account_key": "user-key-a",
            "user_key": "user-key-a",
            "display_name": "Member A",
            "email": "a@example.com",
        }

    def tearDown(self):
        self._identity_patch.stop()
        app.config.update(self.original)

    def create_entry(self, user_key, entry_key, canonical_type, values):
        return self.entries.commit(user_key, {
            "request_id": str(uuid4()),
            "type": "create",
            "entry_key": entry_key,
            "canonical_type": canonical_type,
            "values": values,
        })

    def test_gate_off_keeps_neutral_summary_without_controls(self):
        app.config["PEERSLATE_MY_DATA_ENABLED"] = False
        response = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a"))
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("read-only summary", html)
        self.assertNotIn("my-data.js", html)
        self.assertNotIn("my-data-bootstrap", html)
        self.assertNotIn("Add information", html)

    def test_gate_on_renders_entrance_with_benefit_copy(self):
        response = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a"))
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Add information", html)
        self.assertIn("Your experience helps PeerSlate work better for you.", html)
        self.assertIn("Your information starts private.", html)
        self.assertIn("Public effects are not active yet.", html)
        self.assertIn("/api/entry-policy/me/entries", html)
        self.assertIn("/api/resume-intake/me", html)
        self.assertIn("my-data.js", html)

    def test_member_copy_avoids_dash_punctuation(self):
        response = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a"))
        html = response.get_data(as_text=True)
        # Member-facing promise: no dash punctuation anywhere in the
        # My Data section (the site shell around it is out of scope).
        start = html.index('id="my-data-title"')
        end = html.index("Member settings actions")
        section = html[start:end]
        for dash in ("\u2013", "\u2014", "--"):
            self.assertNotIn(dash, section)

    def test_anonymous_my_data_redirects_to_sign_in(self):
        response = self.client.get("/app/settings/my-data")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/sign-in", response.headers["Location"])

    def test_two_members_cannot_see_each_others_bootstrap(self):
        self.create_entry("user-key-a", key(1), "skill", {"skill_name": "Python"})
        first = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a"))
        self.assertIn("Python", first.get_data(as_text=True))
        self.first_row.return_value = {
            "account_key": "user-key-b",
            "user_key": "user-key-b",
            "display_name": "Member B",
            "email": "b@example.com",
        }
        second = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-b"))
        self.assertNotIn("Python", second.get_data(as_text=True))

    def test_bootstrap_degrades_truthfully_when_stores_unavailable(self):
        app.config["ENTRY_POLICY_SERVICE"] = None
        app.config["RESUME_INTAKE_SERVICE"] = None
        response = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a"))
        # The SQL-backed globals fail closed without an applied schema; the
        # page must stay up and report the outage instead of breaking.
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("Add information", html)
        self.assertIn('"entries_state": "unavailable"', html)

    def test_member_markup_cannot_break_out_of_bootstrap_json(self):
        self.create_entry(
            "user-key-a", key(1), "skill",
            {"skill_name": "X</script><script>alert(1)</script>"},
        )
        html = self.client.get(
            "/app/settings/my-data", headers=easy_auth_header("member-a")
        ).get_data(as_text=True)
        start = html.index('id="my-data-bootstrap"')
        end = html.index("</script>", start)
        payload = html[start:end]
        self.assertNotIn("</script><script>", payload)
        self.assertIn("X\\u003c/script\\u003e", payload)

    def test_settings_page_hosts_entrance_behind_same_gate(self):
        response = self.client.get(
            "/app/settings", headers=easy_auth_header("member-a"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("Add information", response.get_data(as_text=True))


if __name__ == "__main__":
    unittest.main()

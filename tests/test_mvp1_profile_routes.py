"""Real Flask/Core integration with explicit synthetic owners and persistence."""

from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch
from uuid import uuid4

from services.mvp1_profile_binding import Mvp1ProfileBinding
from services.profile_core_service import InMemoryProfileCoreStore


class Mvp1ProfileRouteTests(TestCase):
    def setUp(self):
        from app import app
        self.app = app
        self.binding = Mvp1ProfileBinding(InMemoryProfileCoreStore())
        self.owner = "member-a"
        config = patch.dict(app.config, {
            "TESTING": True, "PEERSLATE_MVP1_PROFILE_ENABLED": True,
            "MVP1_PROFILE_BINDING": self.binding, "PEERSLATE_ALLOW_DEV_IDENTITY": True,
            "PEERSLATE_DEV_USER_KEY": self.owner, "PEERSLATE_TRUST_EASYAUTH_HEADERS": False,
            "RATELIMIT_ENABLED": False,
        })
        config.start(); self.addCleanup(config.stop)
        identity = patch("mvp1_profile_routes.get_current_identity", side_effect=lambda: SimpleNamespace(user_key=self.owner))
        identity.start(); self.addCleanup(identity.stop)
        self.client = app.test_client()
        self.fields = {"display_name": "Alex River", "headline": "Engineer",
                       "location": None, "summary": "Builds useful tools."}

    def command(self, body, **kwargs):
        return self.client.post("/api/profile/me/commands", json=body,
                                headers={"X-PeerSlate-Request": "same-origin"}, **kwargs)

    def save(self):
        result = self.command({"type": "save", "slug": self.owner,
                               "expected_draft_version": None, "identity": self.fields})
        self.assertEqual(result.status_code, 200, result.get_json())
        self.assertEqual(result.json["outcome"], "saved_private")
        return result.json

    def publish(self, state):
        expected = {"expected_draft_version": state["draft_version"],
                    "expected_public_revision": state["public_revision"]}
        review = self.command({"type": "review", **expected})
        self.assertEqual(review.status_code, 200, review.get_json())
        result = self.command({"type": "publish", **expected,
            "candidate_digest": review.json["review"]["candidate_digest"],
            "request_id": str(uuid4()), "confirmed": True})
        self.assertEqual(result.status_code, 200, result.get_json())
        return result.json

    def test_default_off_is_neutral_and_performs_no_profile_reads(self):
        self.app.config["PEERSLATE_MVP1_PROFILE_ENABLED"] = False
        with patch.object(self.binding.store, "draft_for_owner") as read:
            self.assertEqual(self.client.get("/app/profile").status_code, 404)
            self.assertEqual(self.client.get("/api/profile/me").status_code, 404)
            self.assertEqual(self.client.get("/member-a").status_code, 404)
            read.assert_not_called()

    def test_private_save_review_publication_and_shared_shell(self):
        state = self.save()
        self.assertIsNone(state["public_profile_url"])
        self.assertEqual(self.client.get("/member-a").status_code, 404)
        page = self.client.get("/app/profile")
        self.assertEqual(page.status_code, 200)
        self.assertEqual(page.text.count("<main"), 1)
        self.assertIn("Save privately", page.text)
        published = self.publish(state)
        self.assertEqual(published["public_profile_url"], "/member-a")
        guest = self.client.get("/member-a")
        self.assertEqual(guest.status_code, 200)
        self.assertIn("Alex River", guest.text)
        self.assertNotIn('id="mvp1-profile-form"', guest.text)
        self.assertEqual(guest.text.count("<main"), 1)
        self.assertEqual(guest.headers["Cache-Control"], "private, no-store")

    def test_private_edit_withdraw_and_republish_preserve_real_current_revision(self):
        public = self.publish(self.save())
        saved = self.command({"type": "save", "slug": self.owner,
            "expected_draft_version": public["draft_version"],
            "identity": {**self.fields, "display_name": "Alex Brook"}})
        self.assertEqual(saved.status_code, 200)
        self.assertIn("Alex River", self.client.get("/member-a").text)
        withdrawn = self.command({"type": "withdraw", "request_id": str(uuid4()), "confirmed": True,
                                  "expected_public_revision": public["public_revision"]})
        self.assertEqual(withdrawn.status_code, 200)
        self.assertIsNotNone(withdrawn.json["public_revision"])
        self.assertIsNone(withdrawn.json["public_profile_url"])
        self.assertEqual(self.client.get("/member-a").status_code, 404)
        self.publish(withdrawn.json)
        self.assertIn("Alex Brook", self.client.get("/member-a").text)

    def test_two_owner_private_state_and_forged_context_are_isolated(self):
        state = self.save()
        self.owner = "member-b"
        self.assertIsNone(self.client.get("/api/profile/me").json["identity"])
        foreign = self.command({"type": "save", "slug": "member-b",
            "expected_draft_version": state["draft_version"], "identity": self.fields})
        self.assertEqual(foreign.status_code, 409)
        forged = self.command({"type": "save", "owner_key": "member-a", "identity": self.fields})
        self.assertEqual(forged.status_code, 400)
        self.assertEqual(self.client.get("/unknown-member").status_code, 404)

    def test_cross_origin_write_is_refused_before_store_mutation(self):
        with patch.object(self.binding.store, "put_draft") as write:
            response = self.client.post("/api/profile/me/commands", json={"type": "save"},
                headers={"X-PeerSlate-Request": "same-origin", "Origin": "https://untrusted.example"})
            self.assertEqual(response.status_code, 403)
            write.assert_not_called()

    def test_existing_routes_fixture_addresses_and_other_owners_are_reserved(self):
        for slug in ("app", "petec"):
            response = self.command({"type": "save", "slug": slug, "identity": self.fields})
            self.assertEqual(response.status_code, 400)
        self.save()
        self.owner = "member-b"
        response = self.command({"type": "save", "slug": "member-a", "identity": self.fields})
        self.assertEqual(response.status_code, 409)

    def test_escaped_public_identity_and_no_extra_profile_destinations(self):
        self.fields["summary"] = "<script>throw 'must remain text'</script>"
        self.publish(self.save())
        guest = self.client.get("/member-a")
        self.assertIn("&lt;script&gt;", guest.text)
        self.assertNotIn("<script>throw", guest.text)
        self.assertNotIn('aria-label="Profile destinations"', guest.text)
        self.assertEqual(self.client.get("/member-a/profile-home").status_code, 404)

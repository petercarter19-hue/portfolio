import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase

from services.ai_foundation import Audience, Purpose
from services.ask_pete import load_public_source_catalog
from services.ask_pete.errors import PublicSourceManifestError


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "data" / "ai_sources" / "ask_pete_public_v1.json"
RESUME_PATH = ROOT / "static" / "data" / "resume_data.json"
RESUME_TEMPLATE_PATH = ROOT / "templates" / "resume2.html"


class PublicSourceManifestTests(TestCase):
    def setUp(self) -> None:
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.resume = json.loads(RESUME_PATH.read_text(encoding="utf-8"))

    def load_changed(
        self,
        *,
        manifest: dict | None = None,
        resume: dict | None = None,
    ):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            manifest_path = root / "manifest.json"
            resume_path = root / "resume.json"
            manifest_path.write_text(
                json.dumps(manifest or self.manifest),
                encoding="utf-8",
            )
            resume_path.write_text(
                json.dumps(resume or self.resume),
                encoding="utf-8",
            )
            return load_public_source_catalog(
                manifest_path=manifest_path,
                resume_path=resume_path,
            )

    def test_catalog_loads_only_explicit_public_ai_sources(self) -> None:
        catalog = load_public_source_catalog(
            manifest_path=MANIFEST_PATH,
            resume_path=RESUME_PATH,
        )

        self.assertEqual(catalog.manifest_id, "ask-pete-public-petec-v1")
        self.assertEqual(catalog.subject_key, "petec")
        self.assertEqual(catalog.subject_display_name, "Pete Carter")
        self.assertEqual(len(catalog.records), 15)
        self.assertEqual(
            {record.locator.record_kind for record in catalog.records},
            {"profile", "career_role", "skill", "achievement"},
        )
        for source in catalog.sources:
            self.assertEqual(source.allowed_audiences, frozenset({Audience.PUBLIC}))
            self.assertTrue(source.allowed_purposes)
            self.assertTrue(
                source.allowed_purposes
                <= {
                    Purpose.PUBLIC_PROFILE_ANSWER,
                    Purpose.RECRUITER_BRIEF,
                    Purpose.EVIDENCE_FINDER,
                    Purpose.INTERVIEW_PREPARATION,
                }
            )
            self.assertTrue(source.digest_is_current())

    def test_profile_renderer_excludes_contact_and_legacy_knowledge(self) -> None:
        catalog = load_public_source_catalog(
            manifest_path=MANIFEST_PATH,
            resume_path=RESUME_PATH,
        )
        profile = catalog.record_for_version("ask-pete:profile:petec:v1").source

        self.assertNotIn(self.resume["profile"]["email"], profile.content)
        self.assertNotIn("@", profile.content)
        self.assertNotIn("docs/knowledge", profile.content)
        self.assertNotIn("recruiter_faq.md", profile.content)

    def test_locators_match_the_existing_resume_anchor_contract(self) -> None:
        catalog = load_public_source_catalog(
            manifest_path=MANIFEST_PATH,
            resume_path=RESUME_PATH,
        )
        template = RESUME_TEMPLATE_PATH.read_text(encoding="utf-8")

        for record in catalog.records:
            locator = record.locator
            if locator.record_kind == "profile":
                self.assertIn('id="resume-overview"', template)
            elif locator.record_kind == "career_role":
                self.assertEqual(locator.anchor, f"r2-exp-card-{locator.record_id}")
                self.assertIn('id="r2-exp-card-{{ role.id }}"', template)
            elif locator.record_kind == "skill":
                self.assertEqual(locator.anchor, f"r2-skill-panel-{locator.record_id}")
                self.assertIn('id="r2-skill-panel-{{ skill.id }}"', template)
            else:
                self.assertEqual(locator.anchor, "resume-achievements")
                self.assertIn('id="resume-achievements"', template)

    def test_context_source_is_ordered_first_without_expanding_scope(self) -> None:
        catalog = load_public_source_catalog(
            manifest_path=MANIFEST_PATH,
            resume_path=RESUME_PATH,
        )
        sources = catalog.sources_for(
            Purpose.EVIDENCE_FINDER,
            context_key="skill:mbse",
        )

        self.assertEqual(sources[0].source_version_key, "ask-pete:skill:mbse:v1")
        self.assertEqual(len(sources), 15)

    def test_changed_resume_content_fails_closed_until_reapproved(self) -> None:
        changed = copy.deepcopy(self.resume)
        changed["profile"]["summary"] += " Unapproved new claim."

        with self.assertRaisesRegex(
            PublicSourceManifestError,
            "approved source content digest changed",
        ):
            self.load_changed(resume=changed)

    def test_missing_record_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["records"][0]["record_id"] = "missing"
        changed["records"][0]["locator"]["record_id"] = "missing"

        with self.assertRaisesRegex(
            PublicSourceManifestError,
            "approved profile record does not match",
        ):
            self.load_changed(manifest=changed)

    def test_duplicate_source_key_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["records"][1]["source_key"] = changed["records"][0]["source_key"]

        with self.assertRaisesRegex(
            PublicSourceManifestError,
            "manifest source keys must be unique",
        ):
            self.load_changed(manifest=changed)

    def test_non_public_purpose_fails_closed(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["records"][0]["allowed_purposes"] = ["private_coaching"]

        with self.assertRaisesRegex(
            PublicSourceManifestError,
            "manifest purpose is not public",
        ):
            self.load_changed(manifest=changed)

    def test_ai_use_requires_explicit_approval(self) -> None:
        changed = copy.deepcopy(self.manifest)
        changed["records"][0]["approved_for_ask_pete"] = False

        with self.assertRaisesRegex(
            PublicSourceManifestError,
            "approved_for_ask_pete must be explicitly true",
        ):
            self.load_changed(manifest=changed)

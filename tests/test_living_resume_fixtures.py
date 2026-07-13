import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "static" / "data" / "living_resume_fixtures.json"


class LivingResumeFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.profiles = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
        cls.by_id = {profile["id"]: profile for profile in cls.profiles}

    def test_all_six_required_profile_shapes_exist(self):
        self.assertEqual(
            set(self.by_id),
            {"student", "early-career", "mid-career", "career-changer", "freelancer", "senior"},
        )

    def test_profile_shapes_exercise_variable_career_histories(self):
        student_kinds = {item["kind"] for item in self.by_id["student"]["chapters"]}
        self.assertNotIn("Experience", student_kinds)
        self.assertTrue({"Education", "Project", "Credential", "Future"}.issubset(student_kinds))

        early_roles = [item for item in self.by_id["early-career"]["chapters"] if item["kind"] == "Experience"]
        mid_roles = [item for item in self.by_id["mid-career"]["chapters"] if item["kind"] == "Experience"]
        senior_roles = [item for item in self.by_id["senior"]["chapters"] if item["kind"] == "Experience"]
        freelancer_roles = [item for item in self.by_id["freelancer"]["chapters"] if item["kind"] == "Engagement"]

        self.assertGreaterEqual(len(early_roles), 1)
        self.assertLessEqual(len(early_roles), 2)
        self.assertGreaterEqual(len(mid_roles), 3)
        self.assertLessEqual(len(mid_roles), 5)
        self.assertGreaterEqual(len(senior_roles), 8)
        self.assertGreaterEqual(len(freelancer_roles), 3)
        self.assertIn(
            "Transition",
            {item["kind"] for item in self.by_id["career-changer"]["chapters"]},
        )

    def test_every_chapter_has_unique_generic_evidence_ready_content(self):
        fixture_text = FIXTURE_PATH.read_text(encoding="utf-8").lower()
        for prohibited in ("pete carter", "northrop grumman", "l3harris", "micap"):
            self.assertNotIn(prohibited, fixture_text)

        for profile in self.profiles:
            chapter_ids = [chapter["id"] for chapter in profile["chapters"]]
            self.assertEqual(len(chapter_ids), len(set(chapter_ids)))
            for chapter in profile["chapters"]:
                self.assertTrue(chapter["title"])
                self.assertTrue(chapter["summary"])
                self.assertGreaterEqual(len(chapter["outcomes"]), 2)
                self.assertGreaterEqual(len(chapter["skills"]), 2)
                for skill in chapter["skills"]:
                    self.assertTrue(skill["name"])
                    self.assertTrue(skill["proof"])


if __name__ == "__main__":
    unittest.main()

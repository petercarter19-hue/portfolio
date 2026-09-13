"""Unit tests for the My Data presentation facade.

Pure decisions with stubbed backing services: grouping order, search and
filter selection, Activity ordering, real-world versus entry dates, and
truthful unavailable states. No Flask app, database, or provider.
"""

import unittest

from services.my_data_service import MyDataService


def entry(key, category, canonical_type, values, **overrides):
    record = {
        "entry_key": key,
        "canonical_type": canonical_type,
        "category": category,
        "parent_key": None,
        "content_version": 1,
        "access_revision": 1,
        "resume_display": False,
        "visitor_ai": False,
        "private_assistance_excluded": False,
        "lifecycle": "active",
        "recover_until": None,
        "expired": False,
        "values": dict(values),
        "standalone": False,
        "created_at": "2026-09-01T10:00:00Z",
        "updated_at": "2026-09-01T10:00:00Z",
    }
    record.update(overrides)
    return record


class StubEntries:
    def __init__(self, entries=None, unavailable=False):
        self._entries = entries or []
        self._unavailable = unavailable

    def list_entries(self, user_key):
        if self._unavailable:
            raise RuntimeError("store unavailable")
        assert user_key == "owner-a"
        return {"entries": [dict(item) for item in self._entries]}


class StubIntake:
    def __init__(self, workspace=None, unavailable=False):
        self._workspace = workspace or {}
        self._unavailable = unavailable

    def get_workspace(self, user_key):
        if self._unavailable:
            raise RuntimeError("intake unavailable")
        assert user_key == "owner-a"
        return dict(self._workspace)


def overview(entries, workspace=None, **filters):
    service = MyDataService(
        entry_policy=StubEntries(entries),
        intake=StubIntake(workspace or {}),
    )
    return service.overview("owner-a", **filters)


class MyDataGroupingTests(unittest.TestCase):
    def test_groups_follow_member_facing_order_and_skip_empty(self):
        result = overview([
            entry("k1", "skill", "skill", {"skill_name": "Python"}),
            entry("k2", "experience", "role", {
                "role_title": "Engineer", "employer_name": "Acme"}),
        ])
        self.assertEqual(
            [group["key"] for group in result["groups"]],
            ["experience", "skill"],
        )
        self.assertEqual(
            [group["title"] for group in result["groups"]],
            ["Work history", "Skills"],
        )

    def test_deleted_entries_stay_out_of_category_groups(self):
        result = overview([
            entry("k1", "skill", "skill", {"skill_name": "Python"},
                  lifecycle="deleted"),
        ])
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["visible_count"], 0)
        self.assertEqual(result["total_count"], 1)

    def test_permanently_deleted_entries_never_surface(self):
        result = overview(
            [entry("k1", "skill", "skill", {"skill_name": "Python"},
                   lifecycle="permanently_deleted")],
            permission="recently_deleted",
        )
        self.assertEqual(result["visible_count"], 0)


class MyDataSearchFilterTests(unittest.TestCase):
    def test_search_matches_titles_details_and_types(self):
        entries = [
            entry("k1", "experience", "role", {
                "role_title": "Quality Engineer", "employer_name": "Acme"}),
            entry("k2", "skill", "skill", {"skill_name": "Welding"}),
        ]
        self.assertEqual(len(overview(entries, search="quality")["groups"][0]["entries"]), 1)
        self.assertEqual(overview(entries, search="acme")["visible_count"], 1)
        self.assertEqual(overview(entries, search="nope")["visible_count"], 0)

    def test_category_and_permission_filters_combine(self):
        entries = [
            entry("k1", "experience", "role", {
                "role_title": "Engineer", "employer_name": "Acme"}),
            entry("k2", "experience", "role", {
                "role_title": "Manager", "employer_name": "Beta"},
                resume_display=True),
        ]
        result = overview(entries, category="experience", permission="resume")
        self.assertEqual(result["visible_count"], 1)
        self.assertEqual(result["groups"][0]["entries"][0]["entry_key"], "k2")

    def test_private_filter_excludes_shared_and_deleted(self):
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "A"}),
            entry("k2", "skill", "skill", {"skill_name": "B"}, visitor_ai=True),
            entry("k3", "skill", "skill", {"skill_name": "C"},
                  lifecycle="deleted"),
        ]
        result = overview(entries, permission="private")
        self.assertEqual(
            [item["entry_key"] for item in result["groups"][0]["entries"]],
            ["k1"],
        )

    def test_recently_deleted_filter_shows_only_deleted(self):
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "A"}),
            entry("k2", "skill", "skill", {"skill_name": "B"},
                  lifecycle="deleted"),
        ]
        result = overview(entries, permission="recently_deleted")
        self.assertEqual(
            [item["entry_key"] for item in result["groups"][0]["entries"]],
            ["k2"],
        )

    def test_combined_permissions_match_both_filters(self):
        both = entry(
            "k1", "skill", "skill", {"skill_name": "Both"},
            resume_display=True, visitor_ai=True,
        )
        resume_only = entry(
            "k2", "skill", "skill", {"skill_name": "Resume"},
            resume_display=True,
        )
        visitor_only = entry(
            "k3", "skill", "skill", {"skill_name": "Visitor"},
            visitor_ai=True,
        )
        entries = [both, resume_only, visitor_only]
        resume = overview(entries, permission="resume")
        visitor = overview(entries, permission="visitor_ai")
        self.assertEqual(
            [item["entry_key"]
             for group in resume["groups"] for item in group["entries"]],
            ["k1", "k2"],
        )
        self.assertEqual(
            [item["entry_key"]
             for group in visitor["groups"] for item in group["entries"]],
            ["k1", "k3"],
        )
        self.assertEqual(overview(entries, permission="private")["visible_count"], 0)

    def test_exclusion_coexists_with_other_states(self):
        excluded_private = entry(
            "k1", "skill", "skill", {"skill_name": "Excluded"},
            private_assistance_excluded=True,
        )
        excluded_shared = entry(
            "k2", "skill", "skill", {"skill_name": "ExcludedResume"},
            resume_display=True, private_assistance_excluded=True,
        )
        entries = [excluded_private, excluded_shared]
        self.assertEqual(
            [item["entry_key"]
             for group in overview(entries, permission="excluded")["groups"]
             for item in group["entries"]],
            ["k1", "k2"],
        )
        # Exclusion alone stays private; exclusion with sharing is shared.
        self.assertEqual(
            [item["entry_key"]
             for group in overview(entries, permission="private")["groups"]
             for item in group["entries"]],
            ["k1"],
        )
        self.assertEqual(overview(entries, permission="resume")["visible_count"], 1)

    def test_deleted_entry_with_exclusion_reports_lifecycle(self):
        deleted = entry(
            "k1", "skill", "skill", {"skill_name": "Gone"},
            lifecycle="deleted", private_assistance_excluded=True,
        )
        result = overview([deleted], permission="recently_deleted")
        self.assertEqual(result["visible_count"], 1)
        self.assertEqual(overview([deleted], permission="all")["visible_count"], 0)
        self.assertEqual(
            overview([deleted], permission="excluded")["visible_count"], 0
        )

    def test_unknown_view_and_permission_fall_back(self):
        result = overview([], view="timeline", permission="everyone")
        self.assertEqual(result["view"], "category")
        self.assertEqual(result["permission"], "all")


class MyDataActivityTests(unittest.TestCase):
    def test_activity_orders_newest_first_across_sources(self):
        workspace = {
            "pending_proposals": [
                {"proposal_key": "p1", "kind": "new",
                 "created_at": "2026-09-03T10:00:00Z", "target_key": None},
            ],
            "last_receipt": {"created_at": "2026-09-02T10:00:00Z"},
        }
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "Python"},
                  created_at="2026-09-01T10:00:00Z",
                  updated_at="2026-09-04T10:00:00Z"),
        ]
        result = overview(entries, workspace)
        kinds = [event["kind"] for event in result["activity"]]
        # Newest first: the Sept 4 correction outranks the Sept 3 proposal,
        # which outranks the Sept 2 composer receipt.
        self.assertEqual(
            kinds,
            ["entry_updated", "proposal_needs_review", "composer_add"],
        )
        self.assertEqual(result["activity"][0]["entry_key"], "k1")
        self.assertEqual(result["activity"][1]["kind"], "proposal_needs_review")

    def test_real_world_dates_never_become_activity_dates(self):
        entries = [
            entry("k1", "experience", "role", {
                "role_title": "Engineer", "employer_name": "Acme",
                "start_date": "2019-01-01", "end_date": "2023-05-31"},
                created_at="2026-09-01T10:00:00Z",
                updated_at="2026-09-01T10:00:00Z"),
        ]
        result = overview(entries, {})
        self.assertEqual(len(result["activity"]), 1)
        self.assertEqual(result["activity"][0]["at"], "2026-09-01T10:00:00Z")

    def test_deletion_uses_the_lifecycle_timestamp(self):
        # Content corrected September 2, deleted September 13: the
        # deletion event is dated September 13, never September 2.
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "Python"},
                  lifecycle="deleted",
                  created_at="2026-09-01T10:00:00Z",
                  updated_at="2026-09-02T10:00:00Z",
                  deleted_at="2026-09-13T10:00:00Z"),
        ]
        result = overview(entries, {})
        self.assertEqual(result["activity"][0]["kind"], "entry_deleted")
        self.assertEqual(
            result["activity"][0]["at"], "2026-09-13T10:00:00Z"
        )

    def test_deletion_without_a_lifecycle_timestamp_invents_no_event(self):
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "Python"},
                  lifecycle="deleted",
                  created_at="2026-09-01T10:00:00Z",
                  updated_at="2026-09-05T10:00:00Z"),
        ]
        result = overview(entries, {})
        self.assertEqual(result["activity"], [])

    def test_unchanged_entry_reads_as_added_not_corrected(self):
        # An equivalent-match resolution that adopts identical values
        # leaves updated_at equal to created_at, so Activity must not
        # report a correction that never happened.
        entries = [
            entry("k1", "skill", "skill", {"skill_name": "Python"},
                  created_at="2026-09-01T10:00:00Z",
                  updated_at="2026-09-01T10:00:00Z"),
        ]
        result = overview(entries, {})
        self.assertEqual(result["activity"][0]["kind"], "entry_added")

    def test_entries_without_timestamps_stay_out_of_activity(self):
        record = entry("k1", "skill", "skill", {"skill_name": "Python"})
        del record["created_at"]
        del record["updated_at"]
        result = overview([record], {})
        self.assertEqual(result["activity"], [])


class MyDataUnavailableTests(unittest.TestCase):
    def test_entry_outage_is_a_state_not_an_exception(self):
        service = MyDataService(
            entry_policy=StubEntries(unavailable=True),
            intake=StubIntake({}),
        )
        result = service.overview("owner-a")
        self.assertEqual(result["entries_state"], "unavailable")
        self.assertEqual(result["groups"], [])
        self.assertEqual(result["total_count"], 0)

    def test_intake_outage_keeps_entry_activity(self):
        service = MyDataService(
            entry_policy=StubEntries([
                entry("k1", "skill", "skill", {"skill_name": "Python"}),
            ]),
            intake=StubIntake(unavailable=True),
        )
        result = service.overview("owner-a")
        self.assertEqual(result["activity_state"], "intake_unavailable")
        self.assertEqual(len(result["activity"]), 1)
        self.assertEqual(result["activity"][0]["kind"], "entry_added")


if __name__ == "__main__":
    unittest.main()

"""Dedicated contracts for the Community owner SQL verifier."""

from __future__ import annotations

import importlib.util
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERIFIER = (
    ROOT
    / "SQL FIles"
    / "Verification"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_owner_public_verify.sql"
)
RUNNER = ROOT / "scripts" / "apply_sql_migrations.py"
MIGRATION = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community.sql"
)
ROLLBACK = (
    ROOT
    / "SQL FIles"
    / "Migrations"
    / "proposed"
    / "PS-COMMUNITY-PUBLIC-PILOT-001_community_rollback.sql"
)
XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


def load_runner():
    spec = importlib.util.spec_from_file_location("community_migrations", RUNNER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def marker(name, **values):
    return [{"verification_marker": name, **values}]


def media_row(key):
    return {
        "media_key": key,
        "display_name": f"{key}.pdf",
        "content_type": "application/pdf",
        "byte_length": 16,
        "pixel_width": None,
        "pixel_height": None,
    }


def shelf_row(key, body, *, viewer_saved=False):
    return {
        "contribution_key": key,
        "body": body,
        "author_name": "Shelf author",
        "projection_state": "active",
        "viewer_saved": int(viewer_saved),
    }


def valid_read_contract_results():
    post_key = "post"
    root_key = "root"
    hidden_key = "hidden"
    selected_key = "selected"
    omitted_key = "omitted"
    post_media_key = "post-media"
    root_media_key = "root-media"
    hidden_media_key = "hidden-media"
    selected_media_key = "selected-media"
    results = []

    results.extend(
        [
            marker(
                "structural_conversation",
                expected_post_key=post_key,
                expected_root_key=root_key,
                expected_hidden_key=hidden_key,
                expected_selected_key=selected_key,
                expected_omitted_leaf_key=omitted_key,
                expected_post_media_key=post_media_key,
                expected_root_media_key=root_media_key,
                expected_hidden_media_key=hidden_media_key,
                expected_selected_media_key=selected_media_key,
            ),
            [{"post_key": post_key}],
            [
                {
                    "contribution_key": root_key,
                    "projection_state": "active",
                    "body": "root body",
                    "author_name": "Root author",
                    "parent_contribution_key": None,
                    "child_reply_count": 0,
                },
                {
                    "contribution_key": hidden_key,
                    "projection_state": "unavailable",
                    "body": None,
                    "contribution_kind": None,
                    "author_name": None,
                    "author_avatar_url": None,
                    "parent_contribution_key": root_key,
                    "child_reply_count": 1,
                },
                {
                    "contribution_key": selected_key,
                    "projection_state": "active",
                    "body": "selected body",
                    "author_name": "Selected author",
                    "parent_contribution_key": hidden_key,
                    "child_reply_count": 0,
                },
            ],
            [media_row(post_media_key)],
            [media_row(root_media_key), media_row(selected_media_key)],
            [{"saved": 1, "response_intention": "offer_help"}],
            [{"selected_candidate_count": 3, "has_more": 0}],
            marker("structural_conversation_end"),
        ]
    )

    closure_parent_key = "closure-parent"
    closure_child_key = "closure-child"
    closure_boundary_key = "closure-filler-1"
    closure_rows = [
        {
            "contribution_key": closure_child_key,
            "parent_contribution_key": closure_parent_key,
            "projection_state": "active",
        },
        *[
            {
                "contribution_key": f"closure-filler-{ordinal}",
                "parent_contribution_key": None,
                "projection_state": "active",
            }
            for ordinal in range(19, 0, -1)
        ],
        {
            "contribution_key": closure_parent_key,
            "parent_contribution_key": None,
            "projection_state": "active",
        },
    ]
    results.extend(
        [
            marker(
                "conversation_page_closure",
                expected_post_key=post_key,
                expected_parent_key=closure_parent_key,
                expected_child_key=closure_child_key,
                expected_boundary_key=closure_boundary_key,
            ),
            [{"post_key": post_key}],
            closure_rows,
            [],
            [],
            [{"saved": 1, "response_intention": "offer_help"}],
            [
                {
                    "selected_candidate_count": 21,
                    "has_more": 1,
                    "boundary_created_at_utc": "9998-01-01T00:00:01Z",
                    "boundary_contribution_key": closure_boundary_key,
                }
            ],
            marker("conversation_page_closure_end"),
        ]
    )

    results.extend(
        [
            marker(
                "selected_contribution",
                expected_post_key=post_key,
                expected_root_key=root_key,
                expected_hidden_key=hidden_key,
                expected_selected_key=selected_key,
                expected_root_media_key=root_media_key,
                expected_hidden_media_key=hidden_media_key,
                expected_selected_media_key=selected_media_key,
            ),
            [
                {
                    "contribution_key": selected_key,
                    "projection_state": "active",
                    "body": "selected body",
                    "author_name": "Selected author",
                    "viewer_saved": 1,
                }
            ],
            [media_row(selected_media_key)],
            [
                {
                    "contribution_key": root_key,
                    "projection_state": "active",
                    "body": "root body",
                    "author_name": "Root author",
                    "parent_contribution_key": None,
                },
                {
                    "contribution_key": hidden_key,
                    "projection_state": "unavailable",
                    "body": None,
                    "contribution_kind": None,
                    "author_name": None,
                    "author_avatar_url": None,
                    "parent_contribution_key": root_key,
                },
            ],
            [media_row(root_media_key)],
            marker("selected_contribution_end"),
        ]
    )

    for start, end in (
        ("selected_wrong_post", "selected_wrong_post_end"),
        ("selected_revoked_author", "selected_revoked_author_end"),
        ("selected_revoked_post_author", "selected_revoked_post_author_end"),
    ):
        results.extend([marker(start), [], [], [], [], marker(end)])

    shelf_page_one = [
        shelf_row(f"shelf-{ordinal}", f"Community shelf page {ordinal}")
        for ordinal in range(22, 2, -1)
    ]
    results.extend(
        [
            marker(
                "shelf_page_one",
                expected_post_key=post_key,
                expected_boundary_key="shelf-3",
            ),
            [{"post_key": post_key}],
            shelf_page_one,
            [],
            [
                {
                    "selected_candidate_count": 21,
                    "has_more": 1,
                    "boundary_created_at_utc": "9997-01-01T00:00:03Z",
                    "boundary_contribution_key": "shelf-3",
                }
            ],
            marker("shelf_page_one_end"),
        ]
    )
    shelf_page_two = [
        shelf_row("shelf-2", "Community shelf page 2"),
        shelf_row("shelf-1", "Community shelf page 1"),
        shelf_row(selected_key, "selected body", viewer_saved=True),
        shelf_row(root_key, "root body"),
    ]
    results.extend(
        [
            marker("shelf_page_two", expected_post_key=post_key),
            [{"post_key": post_key}],
            shelf_page_two,
            [media_row(root_media_key), media_row(selected_media_key)],
            [{"selected_candidate_count": 4, "has_more": 0}],
            marker("shelf_page_two_end"),
        ]
    )

    for start, end, expected_key, selected_count, has_more, extra in (
        (
            "feed_boundary_page_one",
            "feed_boundary_page_one_end",
            "feed-top",
            1,
            True,
            {},
        ),
        (
            "feed_boundary_page_two_after_revoke",
            "feed_boundary_page_two_after_revoke_end",
            "feed-next",
            1,
            False,
            {"revoked_post_key": "feed-top"},
        ),
    ):
        results.extend(
            [
                marker(
                    start,
                    expected_post_key=expected_key,
                    expected_selected_candidate_count=selected_count,
                    expected_has_more=has_more,
                    **extra,
                ),
                [{"post_key": expected_key}],
                [],
                [],
                [],
                [{"post_key": expected_key}],
                [
                    {
                        "selected_candidate_count": selected_count,
                        "has_more": has_more,
                        "boundary_published_at_utc": "0001-01-01T00:00:01Z",
                        "boundary_post_key": expected_key,
                    }
                ],
                marker(end),
            ]
        )

    return results


def marker_indexes(result_sets):
    return {
        rows[0]["verification_marker"]: index
        for index, rows in enumerate(result_sets)
        if len(rows) == 1 and rows[0].get("verification_marker")
    }


def valid_cleanup_selector_results():
    return [
        marker(
            "cleanup_post_selector",
            expected_post_key="post",
            expected_media_key="post-media",
        ),
        [{"media_key": "post-media", "cleanup_claim_token": "post-token"}],
        marker(
            "cleanup_contribution_selector",
            expected_contribution_key="contribution",
            expected_media_key="contribution-media",
        ),
        [
            {
                "media_key": "contribution-media",
                "cleanup_claim_token": "contribution-token",
            }
        ],
    ]


class CommunityPublicPilotVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.runner = load_runner()

    def test_savepoint_names_fit_the_sql_server_limit(self):
        # SAVE TRANSACTION names are capped at 32 characters, unlike ordinary
        # identifiers at 128. CommunityMediaCompletionCompensation was 36 and
        # failed the whole migration at execution time with error 103; static
        # checks never caught it because the file is otherwise valid T-SQL.
        for path in (MIGRATION, ROLLBACK):
            sql = path.read_text(encoding="utf-8")
            names = set(re.findall(r"SAVE\s+TRANSACTION\s+([A-Za-z0-9_@#]+)", sql))
            rolled = set(
                re.findall(r"ROLLBACK\s+TRANSACTION\s+([A-Za-z0-9_@#]+)", sql)
            )
            for name in names | rolled:
                with self.subTest(path=path.name, savepoint=name):
                    self.assertLessEqual(
                        len(name),
                        32,
                        f"savepoint {name!r} is {len(name)} characters; "
                        "SQL Server truncates at 32 and raises error 103",
                    )
            # Every rolled-back savepoint must actually be declared.
            self.assertTrue(
                rolled <= names,
                f"{path.name} rolls back undeclared savepoints: {rolled - names}",
            )

    def test_sql_verifier_covers_new_read_contracts_inside_outer_rollback(self):
        sql = VERIFIER.read_text(encoding="utf-8")
        runner_source = RUNNER.read_text(encoding="utf-8")
        markers = set(
            re.findall(r"SELECT N'([^']+)' AS verification_marker", sql)
        )

        self.assertTrue(self.runner.COMMUNITY_READ_CONTRACT_MARKERS <= markers)
        self.assertTrue(
            self.runner.COMMUNITY_CLEANUP_SELECTOR_MARKERS <= markers
        )
        self.assertIn("BEGIN TRANSACTION", sql)
        self.assertIn("ROLLBACK TRANSACTION", sql)
        self.assertIn("OBJECT_DEFINITION(OBJECT_ID(N'dbo.usp_ListPublicCommunityFeed'", sql)
        self.assertIn("@SelectedCandidateCount int=(SELECT COUNT(*) FROM @Page)", sql)
        self.assertIn("SELECT TOP (@PageLimit + 1)", sql)
        self.assertIn("@EmittedCandidateCount int=CASE", sql)
        self.assertIn(
            "SELECT @EmittedCandidateCount AS selected_candidate_count",
            sql,
        )
        self.assertIn("AS bit) AS has_more", sql)
        self.assertIn(
            "REPLACE(@FeedProcedureDefinition,N'page_record.page_rank<=@PageLimit',N'')",
            sql,
        )
        self.assertIn("SELECT N''depth_limit'' AS outcome", sql)
        self.assertIn(
            "SET @ContributionKind=CASE WHEN @ParentId IS NOT NULL THEN "
            "N''reply'' WHEN @PostAuthorId=@UserId THEN N''author_update'' "
            "ELSE N''comment'' END",
            sql,
        )
        self.assertIn("sys.parameters", sql)
        self.assertNotIn("@ContributionKind=N'", sql)
        self.assertIn("contribution_kind=N'author_update'", sql)
        self.assertIn("contribution_kind=N'comment'", sql)
        self.assertIn("EXEC dbo.usp_ListPublicCommunityShelf", sql)
        self.assertIn("EXEC dbo.usp_GetPublicCommunityContribution", sql)
        self.assertIn("conversation_page_closure", sql)
        self.assertIn("@ContributionCandidates", sql)
        self.assertIn("WHERE candidate.page_rank<=@PageSize", sql)
        self.assertIn("usp_ReservePublicCommunityMedia", sql)
        self.assertIn("usp_MarkPublicCommunityMediaUploaded", sql)
        self.assertIn("usp_CompletePublicCommunityMedia", sql)
        self.assertIn("@XlsxContentType", sql)
        self.assertIn("@ConstraintHashProperty", sql)
        self.assertIn("@IndexHashProperty", sql)
        self.assertIn("sys.foreign_key_columns", sql)
        self.assertIn("UPDATE dbo.app_users SET active=0 WHERE id=@UserIdB", sql)
        self.assertIn("UPDATE dbo.app_users SET active=0 WHERE id=@UserIdA", sql)
        self.assertIn("@AfterPublishedAtUtc=@FeedTopPublishedAtUtc", sql)
        self.assertIn(
            "usp_ClaimPublicCommunityMediaCleanup @Take=20,@PostKey=@CleanupPostKey",
            sql,
        )
        self.assertIn(
            "@PostSelectorContributionMediaKey,@UserIdA,@CleanupContributionId",
            sql,
        )
        self.assertIn(
            "Post-key cleanup selector claimed media from an active source.",
            sql,
        )
        self.assertIn(
            "usp_ClaimPublicCommunityMediaCleanup @Take=4,@ContributionKey=@MiddleContributionKey",
            sql,
        )
        self.assertNotIn("WAITFOR", sql.upper())
        self.assertIn(
            "_validate_community_read_contracts(result_sets, marker_indexes)",
            runner_source,
        )

    def test_migration_strictly_allows_xlsx_as_a_bounded_document(self):
        migration = MIGRATION.read_text(encoding="utf-8")

        self.assertIn("content_type nvarchar(100) NOT NULL", migration)
        self.assertIn("@ContentType nvarchar(100)", migration)
        self.assertNotIn("content_type nvarchar(40)", migration)
        self.assertNotIn("@ContentType nvarchar(40)", migration)
        self.assertIn("AND max_length=200", migration)

        self.assertIn(
            "CK_community_media_type CHECK (content_type IN "
            "(N'image/jpeg', N'image/png', N'application/pdf', "
            f"N'{XLSX_CONTENT_TYPE}'))",
            migration,
        )
        self.assertIn(
            "@ContentType NOT IN(N''image/jpeg'',N''image/png'',"
            f"N''application/pdf'',N''{XLSX_CONTENT_TYPE}'')",
            migration,
        )
        self.assertIn(
            "content_type IN(N''application/pdf'',"
            f"N''{XLSX_CONTENT_TYPE}'') AND @PixelWidth IS NULL "
            "AND @PixelHeight IS NULL AND @SafeByteLength=byte_length "
            "AND @SafeSha256=sha256",
            migration,
        )

        self.assertIn(
            "CK_community_media_size CHECK (byte_length BETWEEN 1 AND 10485760)",
            migration,
        )
        self.assertIn("IF @AttachmentCount > 4", migration)
        self.assertIn("IF @AttachmentCount>4", migration)

        compensation = migration.split(
            "CREATE OR ALTER PROCEDURE dbo.usp_CompensatePublicCommunityMediaCompletion",
            1,
        )[1].split("CREATE OR ALTER PROCEDURE dbo.", 1)[0]
        self.assertIn(
            "@ContentType IN(N''image/jpeg'',N''image/png'')", compensation
        )
        self.assertNotIn(XLSX_CONTENT_TYPE, compensation)
        self.assertIn("PS_COMMUNITY_PUBLIC_PILOT_001_CONSTRAINT_HASH", migration)
        self.assertIn("PS_COMMUNITY_PUBLIC_PILOT_001_INDEX_HASH", migration)
        self.assertIn("property.class=7", migration)
        self.assertIn("STRING_AGG", migration)
        self.assertIn("OBJECT_DEFINITION(actual.object_id) IS NULL", migration)
        self.assertIn("sys.foreign_key_columns", migration)

    def test_cleanup_selector_validator_accepts_exact_content_free_claims(self):
        results = valid_cleanup_selector_results()
        self.runner._validate_community_cleanup_selectors(
            results, marker_indexes(results)
        )

    def test_cleanup_selector_validator_rejects_cross_selector_media(self):
        results = valid_cleanup_selector_results()
        results[1][0]["media_key"] = "contribution-media"
        with self.assertRaisesRegex(
            RuntimeError, "cleanup selector contract failed"
        ):
            self.runner._validate_community_cleanup_selectors(
                results, marker_indexes(results)
            )

    def test_read_contract_validator_accepts_complete_evidence(self):
        results = valid_read_contract_results()
        self.runner._validate_community_read_contracts(
            results, marker_indexes(results)
        )

    def test_read_contract_validator_rejects_tombstone_content_leak(self):
        results = valid_read_contract_results()
        structural_index = marker_indexes(results)["structural_conversation"]
        hidden_row = results[structural_index + 2][1]
        hidden_row["body"] = "must not escape"

        with self.assertRaisesRegex(RuntimeError, "tombstone exposed hidden content"):
            self.runner._validate_community_read_contracts(
                results, marker_indexes(results)
            )

    def test_read_contract_validator_rejects_partial_selected_media(self):
        results = valid_read_contract_results()
        selected_index = marker_indexes(results)["selected_contribution"]
        results[selected_index + 2][0].pop("display_name")

        with self.assertRaisesRegex(RuntimeError, "full attachments"):
            self.runner._validate_community_read_contracts(
                results, marker_indexes(results)
            )

    def test_read_contract_validator_rejects_shelf_page_overlap(self):
        results = valid_read_contract_results()
        shelf_two_index = marker_indexes(results)["shelf_page_two"]
        results[shelf_two_index + 2][0]["contribution_key"] = "shelf-22"

        with self.assertRaisesRegex(RuntimeError, "skipped or duplicated"):
            self.runner._validate_community_read_contracts(
                results, marker_indexes(results)
            )

    def test_read_contract_validator_rejects_orphaned_conversation_page_child(self):
        results = valid_read_contract_results()
        closure_index = marker_indexes(results)["conversation_page_closure"]
        closure_rows = results[closure_index + 2]
        closure_rows[:] = [
            row
            for row in closure_rows
            if row.get("contribution_key") != "closure-parent"
        ]

        with self.assertRaisesRegex(RuntimeError, "ancestor closure"):
            self.runner._validate_community_read_contracts(
                results, marker_indexes(results)
            )

    def test_read_contract_validator_rejects_feed_boundary_content(self):
        results = valid_read_contract_results()
        feed_index = marker_indexes(results)["feed_boundary_page_one"]
        results[feed_index + 6][0]["body"] = "must not enter a cursor boundary"

        with self.assertRaisesRegex(RuntimeError, "Feed boundary contract failed"):
            self.runner._validate_community_read_contracts(
                results, marker_indexes(results)
            )

    def test_feed_verifier_distinguishes_plus_one_from_exact_full(self):
        for marker_name, incorrect_has_more in (
            ("feed_boundary_page_one", False),
            ("feed_boundary_page_two_after_revoke", True),
        ):
            with self.subTest(marker=marker_name):
                results = valid_read_contract_results()
                feed_index = marker_indexes(results)[marker_name]
                results[feed_index + 6][0]["has_more"] = incorrect_has_more

                with self.assertRaisesRegex(
                    RuntimeError, "Feed boundary contract failed"
                ):
                    self.runner._validate_community_read_contracts(
                        results, marker_indexes(results)
                    )


if __name__ == "__main__":
    unittest.main()

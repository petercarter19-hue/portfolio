"""Contract tests for the synthetic Resume media repository seam.

Evidence level: local unit/contract against the in-memory double. These tests
prove cursor, pagination, persistence, immutability, atomic rollback, receipt,
and owner-isolation contracts. They do not prove SQL, storage, identity, or
deployment behavior.
"""

import unittest
from dataclasses import FrozenInstanceError, replace

from services.resume_media_repository import (
    CATALOG_PAGE_SIZE_LIMIT,
    COMMAND_ADD_MEDIA,
    COMMAND_KEEP_WORDS_ONLY,
    COMMAND_PUBLISH,
    LIFECYCLE_ACTIVE,
    LIFECYCLE_DELETED,
    LIFECYCLE_RESTRICTED,
    LIFECYCLE_WITHDRAWN,
    READINESS_FAILED,
    READINESS_READY,
    SLOT_EXPERIENCE_SUPPORT,
    SLOT_STORY_BANNER,
    SOURCE_KIND_GENERATED_ILLUSTRATION,
    SOURCE_KIND_OWNER_PHOTO,
    CropRect,
    InMemoryResumeMediaRepository,
    MediaPlacement,
    RequestReceipt,
    ResumeMediaRepositoryError,
    canonical_json,
    catalog_provenance_view,
    catalog_rights_view,
    provenance_label_for,
    sha256_hex,
)


OWNER_A = "owner-aaaa1111"
OWNER_B = "owner-bbbb2222"


ALT_TEXT = "Described for assistive technology"

# Crops already shaped for each slot aspect (catalog sources are 1600x900 and
# seeded owner photos are 1200x800 in these tests).
ART_BANNER_CROP = CropRect(x=0.05, y=0.2, width=0.84375, height=0.5)
ART_EXPERIENCE_CROP = CropRect(x=0.2, y=0.2, width=0.50625, height=0.6)
PHOTO_BANNER_CROP = CropRect(x=0.1, y=0.2, width=0.6, height=0.3)
PHOTO_EXPERIENCE_CROP = CropRect(x=0.1, y=0.2, width=0.5, height=0.5)


def catalog_placement(record, slot, *, crop=None, alt_text=ALT_TEXT,
                      decorative=True, caption=None, presentation_version=1,
                      provenance_label=None, digest=None, version=None, asset_id=None):
    """One valid persisted catalog placement for a seeded asset record."""

    return MediaPlacement(
        slot=slot,
        source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION,
        asset_id=asset_id if asset_id is not None else record.asset_id,
        asset_version=record.version if version is None else version,
        asset_digest=record.digest if digest is None else digest,
        crop=crop or (
            ART_BANNER_CROP if slot == SLOT_STORY_BANNER else ART_EXPERIENCE_CROP
        ),
        presentation_version=presentation_version,
        alt_text=alt_text,
        decorative=decorative,
        provenance_label=(
            provenance_label
            if provenance_label is not None
            else provenance_label_for(
                source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION, record=record
            )
        ),
        caption=caption,
    )


def photo_placement(record, slot, *, crop=None, alt_text=ALT_TEXT,
                    decorative=False, caption=None, presentation_version=1,
                    provenance_label=None, digest=None, version=None,
                    source_id=None):
    """One valid persisted owner-photo placement for a seeded source record."""

    return MediaPlacement(
        slot=slot,
        source_kind=SOURCE_KIND_OWNER_PHOTO,
        asset_id=source_id if source_id is not None else record.source_id,
        asset_version=record.version if version is None else version,
        asset_digest=record.digest if digest is None else digest,
        crop=crop or (
            PHOTO_BANNER_CROP if slot == SLOT_STORY_BANNER else PHOTO_EXPERIENCE_CROP
        ),
        presentation_version=presentation_version,
        alt_text=alt_text,
        decorative=decorative,
        provenance_label=(
            provenance_label
            if provenance_label is not None
            else provenance_label_for(source_kind=SOURCE_KIND_OWNER_PHOTO)
        ),
        caption=caption,
    )


def receipt(owner_id, *, command=COMMAND_ADD_MEDIA, uuid="req-1", digest="s" * 64,
            outcome=None):
    return RequestReceipt.create(
        owner_id=owner_id,
        command_type=command,
        request_uuid=uuid,
        semantic_digest=digest,
        outcome=outcome or {"command": command, "outcome": "committed"},
    )


class CatalogSearchTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.repository.seed_catalog_asset(
            asset_id="art-meadow",
            label="Sunset   Meadow",
            category="Landscape",
            tags=("calm", "golden"),
            width=1600,
            height=900,
            digest="a" * 64,
        )
        self.repository.seed_catalog_asset(
            asset_id="art-aurora",
            label="Aurora Sky",
            category="Night",
            tags=("sky",),
            width=1200,
            height=1200,
            digest="b" * 64,
        )
        self.repository.seed_catalog_asset(
            asset_id="art-studio",
            label="bright studio desk",
            category="Work",
            tags=("calm", "interior"),
            width=1400,
            height=900,
            digest="c" * 64,
        )

    def test_search_normalizes_case_whitespace_and_width(self):
        page = self.repository.list_catalog(query="  sunset   MEADOW ", limit=10)
        self.assertEqual([item.asset_id for item in page.items], ["art-meadow"])
        self.repository.seed_catalog_asset(
            asset_id="art-wide",
            label="\uff21\uff55\uff52\uff4f\uff52\uff41 \uff2e\uff49\uff47\uff48\uff54",
            category="Night",
            tags=("sky",),
            digest="9" * 64,
        )
        page = self.repository.list_catalog(query="aurora night", limit=10)
        self.assertEqual([item.asset_id for item in page.items], ["art-wide"])

    def test_filter_by_category_and_tags_uses_all_tags(self):
        page = self.repository.list_catalog(category="landscape", limit=10)
        self.assertEqual([item.asset_id for item in page.items], ["art-meadow"])
        page = self.repository.list_catalog(tags=["CALM"], limit=10)
        self.assertEqual(
            [item.asset_id for item in page.items], ["art-studio", "art-meadow"]
        )
        page = self.repository.list_catalog(tags=["calm", "interior"], limit=10)
        self.assertEqual([item.asset_id for item in page.items], ["art-studio"])

    def test_ordering_is_deterministic_independent_of_insertion_order(self):
        other = InMemoryResumeMediaRepository()
        for asset_id, label in (
            ("art-studio", "bright studio desk"),
            ("art-aurora", "Aurora Sky"),
            ("art-meadow", "Sunset   Meadow"),
        ):
            other.seed_catalog_asset(
                asset_id=asset_id, label=label, category="Any", tags=(), digest="e" * 64
            )
        first = [item.asset_id for item in self.repository.list_catalog(limit=10).items]
        second = [item.asset_id for item in other.list_catalog(limit=10).items]
        self.assertEqual(first, second)
        self.assertEqual(first, ["art-aurora", "art-studio", "art-meadow"])

    def test_zero_results_are_honest(self):
        page = self.repository.list_catalog(query="nothing-matches-this", limit=10)
        self.assertEqual(page.items, ())
        self.assertIsNone(page.next_cursor)
        self.assertEqual(page.total_matches, 0)

    def test_latest_active_version_is_listed_once(self):
        self.repository.seed_catalog_asset(
            asset_id="art-meadow",
            label="Sunset   Meadow",
            category="Landscape",
            tags=("calm", "golden"),
            version=2,
            digest="f" * 64,
        )
        page = self.repository.list_catalog(query="meadow", limit=10)
        self.assertEqual(len(page.items), 1)
        self.assertEqual(page.items[0].version, 2)

    def test_pagination_is_bounded_complete_and_stable(self):
        for index in range(9):
            self.repository.seed_catalog_asset(
                asset_id=f"art-page-{index}",
                label=f"page item {index}",
                category="Paged",
                tags=("page",),
                digest=sha256_hex(f"page-{index}"),
            )
        seen = []
        cursor = None
        pages = 0
        while True:
            page = self.repository.list_catalog(
                query="page", limit=3, cursor=cursor
            )
            self.assertLessEqual(len(page.items), 3)
            self.assertEqual(page.total_matches, 9)
            seen.extend(item.asset_id for item in page.items)
            pages += 1
            cursor = page.next_cursor
            if cursor is None:
                break
        self.assertEqual(sorted(seen), sorted(set(seen)))
        self.assertEqual(len(seen), 9)
        self.assertEqual(pages, 3)
        for index in range(9, 40):
            self.repository.seed_catalog_asset(
                asset_id=f"art-page-{index}",
                label=f"page item {index}",
                category="Paged",
                tags=("page",),
                digest=sha256_hex(f"page-{index}"),
            )
        clamped = self.repository.list_catalog(query="page", limit=1000)
        self.assertEqual(len(clamped.items), CATALOG_PAGE_SIZE_LIMIT)
        self.assertIsNotNone(clamped.next_cursor)
        self.assertEqual(clamped.total_matches, 40)

    def test_cursor_reused_with_different_query_conflicts(self):
        cursor = self.repository.list_catalog(query="calm", limit=1).next_cursor
        self.assertIsNotNone(cursor)
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.list_catalog(query="studio", limit=1, cursor=cursor)
        self.assertEqual(caught.exception.code, "cursor-mismatch")

    def test_malformed_or_tampered_cursor_is_refused(self):
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.list_catalog(limit=1, cursor="not-a-cursor!!")
        self.assertEqual(caught.exception.code, "invalid-cursor")
        cursor = self.repository.list_catalog(limit=1).next_cursor
        tampered = ("B" if cursor[0] != "B" else "C") + cursor[1:]
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.list_catalog(limit=1, cursor=tampered)
        self.assertEqual(caught.exception.code, "invalid-cursor")

    def test_withdrawn_asset_leaves_search_and_authorization(self):
        withdrawn = self.repository.get_catalog_asset("art-meadow")
        self.repository.set_catalog_lifecycle(
            asset_id="art-meadow", version=1, lifecycle=LIFECYCLE_WITHDRAWN
        )
        page = self.repository.list_catalog(query="meadow", limit=10)
        self.assertEqual(page.items, ())
        authorization = self.repository.get_media_authorization(
            owner_id=OWNER_A,
            placement=catalog_placement(withdrawn, SLOT_STORY_BANNER),
        )
        self.assertIsNone(authorization)


class PlacementPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.art = self.repository.seed_catalog_asset(
            asset_id="art-1",
            label="Quiet Forest",
            category="Nature",
            tags=("forest",),
            digest="a" * 64,
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": "catalog/art-1/story_banner.png",
                    "digest": "1" * 64,
                    "content_type": "image/png",
                    "byte_length": 21,
                },
                {
                    "slot": SLOT_EXPERIENCE_SUPPORT,
                    "ref": "catalog/art-1/experience_support.png",
                    "digest": "2" * 64,
                    "content_type": "image/png",
                    "byte_length": 26,
                },
            ),
        )

    def test_crops_persist_separately_per_slot_for_one_asset(self):
        banner_crop = CropRect(x=0.1, y=0.2, width=0.5, height=0.25)
        experience_crop = CropRect(x=0.0, y=0.0, width=0.4, height=0.4)
        stored = self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(
                catalog_placement(self.art, SLOT_STORY_BANNER, crop=banner_crop),
                catalog_placement(
                    self.art, SLOT_EXPERIENCE_SUPPORT, crop=experience_crop
                ),
            ),
            receipt=receipt(OWNER_A),
        )
        self.assertEqual(stored.version, 1)
        reloaded = self.repository.get_draft(OWNER_A)
        self.assertEqual(reloaded, stored)
        self.assertEqual(reloaded.placement_for(SLOT_STORY_BANNER).crop, banner_crop)
        self.assertEqual(
            reloaded.placement_for(SLOT_EXPERIENCE_SUPPORT).crop, experience_crop
        )
        self.assertNotEqual(
            reloaded.placement_for(SLOT_STORY_BANNER).crop,
            reloaded.placement_for(SLOT_EXPERIENCE_SUPPORT).crop,
        )

    def test_committed_snapshots_are_immutable(self):
        provenance = {"model": "synthetic-art-v1"}
        prov = self.repository.seed_catalog_asset(
            asset_id="art-prov",
            label="Provenance",
            category="Nature",
            digest="b" * 64,
            provenance=provenance,
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": "catalog/art-prov/story_banner.png",
                    "digest": "3" * 64,
                    "content_type": "image/png",
                    "byte_length": 7,
                },
            ),
        )
        provenance["model"] = "mutated-after-seed"
        self.assertEqual(
            dict(self.repository.get_catalog_asset("art-prov").provenance)["model"],
            "synthetic-art-v1",
        )
        with self.assertRaises(TypeError):
            self.repository.get_catalog_asset("art-prov").provenance["model"] = "x"
        stored = self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(catalog_placement(prov, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A),
        )
        before = self.repository.snapshot()
        with self.assertRaises(FrozenInstanceError):
            stored.placements[0].crop.x = 0.5
        self.assertEqual(self.repository.get_draft(OWNER_A), stored)
        self.assertEqual(self.repository.snapshot(), before)

    def test_receipt_round_trip_and_conflicting_digest(self):
        stored_receipt = receipt(OWNER_A, uuid="req-77", digest="s" * 64)
        self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(),
            receipt=stored_receipt,
        )
        loaded = self.repository.get_receipt(
            owner_id=OWNER_A, command_type=COMMAND_ADD_MEDIA, request_uuid="req-77"
        )
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.semantic_digest, "s" * 64)
        self.assertEqual(loaded.outcome["outcome"], "committed")
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_draft(
                owner_id=OWNER_A,
                expected_version=1,
                placements=(),
                receipt=receipt(OWNER_A, uuid="req-77", digest="z" * 64),
            )
        self.assertEqual(caught.exception.code, "receipt-conflict")

    def test_owner_isolation_across_drafts_receipts_and_photos(self):
        self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(),
            receipt=receipt(OWNER_A),
        )
        self.repository.seed_owner_photo(
            owner_id=OWNER_A, source_id="source-1", digest="c" * 64
        )
        self.assertEqual(self.repository.get_draft(OWNER_B).version, 0)
        self.assertEqual(self.repository.get_draft(OWNER_B).placements, ())
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_B, command_type=COMMAND_ADD_MEDIA, request_uuid="req-1"
            )
        )
        self.assertIsNone(self.repository.get_owner_photo(OWNER_B, "source-1"))


class AtomicityAndRollbackTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.art = self.repository.seed_catalog_asset(
            asset_id="art-1",
            label="Quiet Forest",
            category="Nature",
            digest="a" * 64,
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": "catalog/art-1/story_banner.png",
                    "digest": "1" * 64,
                    "byte_length": 5,
                },
            ),
        )

    def test_draft_commit_rolls_back_after_partial_write(self):
        before = self.repository.snapshot()
        self.repository.inject_failure("commit_draft", step="after_draft")
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_draft(
                owner_id=OWNER_A,
                expected_version=0,
                placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
                receipt=receipt(OWNER_A),
            )
        self.assertEqual(caught.exception.code, "injected-failure")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_A, command_type=COMMAND_ADD_MEDIA, request_uuid="req-1"
            )
        )
        self.assertIn("rollback:commit_draft", self.repository.mutation_log)

    def test_publication_commit_rolls_back_and_keeps_previous_revision(self):
        self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A, uuid="draft-1"),
        )
        first = self.repository.commit_publication(
            owner_id=OWNER_A,
            expected_draft_version=1,
            expected_publication_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            digest="p" * 64,
            receipt=receipt(OWNER_A, command=COMMAND_PUBLISH, uuid="pub-1"),
        )
        self.assertEqual(first.version, 1)
        before = self.repository.snapshot()
        self.repository.inject_failure("commit_publication", step="after_publication")
        with self.assertRaises(ResumeMediaRepositoryError):
            self.repository.commit_publication(
                owner_id=OWNER_A,
                expected_draft_version=1,
                expected_publication_version=1,
                placements=(),
                digest="q" * 64,
                receipt=receipt(OWNER_A, command=COMMAND_PUBLISH, uuid="pub-2"),
            )
        self.assertEqual(self.repository.snapshot(), before)
        current = self.repository.get_publication(OWNER_A)
        self.assertEqual(current.version, 1)
        self.assertEqual(current.digest, "p" * 64)
        self.assertEqual(len(current.placements), 1)

    def test_version_guards_refuse_stale_expected_versions(self):
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_draft(
                owner_id=OWNER_A,
                expected_version=4,
                placements=(),
                receipt=receipt(OWNER_A),
            )
        self.assertEqual(caught.exception.code, "stale-draft")
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_publication(
                owner_id=OWNER_A,
                expected_draft_version=0,
                expected_publication_version=3,
                placements=(),
                digest="p" * 64,
                receipt=receipt(OWNER_A, command=COMMAND_PUBLISH),
            )
        self.assertEqual(caught.exception.code, "stale-publication")


class AuthorizationSeamTests(unittest.TestCase):
    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()

    def test_owner_photo_authorization_requires_ready_active_matching_source(self):
        self.repository.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-1",
            state=READINESS_READY,
            digest="a" * 64,
            width=1400,
            height=500,
            byte_length=17,
            content_type="image/jpeg",
            version=2,
        )
        owner_placement = MediaPlacement(
            slot=SLOT_STORY_BANNER,
            source_kind=SOURCE_KIND_OWNER_PHOTO,
            asset_id="source-1",
            asset_version=2,
            asset_digest="a" * 64,
            crop=CropRect(x=0.0, y=0.0, width=1.0, height=1.0),
            alt_text=ALT_TEXT,
            provenance_label=provenance_label_for(
                source_kind=SOURCE_KIND_OWNER_PHOTO
            ),
        )
        authorized = self.repository.get_media_authorization(
            owner_id=OWNER_A, placement=owner_placement
        )
        self.assertIsNotNone(authorized)
        self.assertEqual(authorized.accessor, "photo_readiness")
        self.assertEqual(authorized.source_id, "source-1")
        self.assertEqual(authorized.expected_digest, "a" * 64)
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_B, placement=owner_placement
            )
        )
        self.repository.update_owner_photo(
            owner_id=OWNER_A, source_id="source-1", state=READINESS_FAILED
        )
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_A, placement=owner_placement
            )
        )
        self.repository.update_owner_photo(
            owner_id=OWNER_A,
            source_id="source-1",
            state=READINESS_READY,
            lifecycle=LIFECYCLE_RESTRICTED,
        )
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_A, placement=owner_placement
            )
        )
        self.repository.update_owner_photo(
            owner_id=OWNER_A,
            source_id="source-1",
            lifecycle=LIFECYCLE_ACTIVE,
            version=3,
        )
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_A, placement=owner_placement
            )
        )

    def test_catalog_authorization_requires_active_slot_derivative(self):
        self.repository.seed_catalog_asset(
            asset_id="art-1",
            label="Quiet Forest",
            category="Nature",
            digest="a" * 64,
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": "catalog/art-1/story_banner.png",
                    "digest": "1" * 64,
                    "byte_length": 5,
                },
            ),
        )
        authorized = self.repository.get_media_authorization(
            owner_id=OWNER_A,
            placement=catalog_placement(
                self.repository.get_catalog_asset("art-1"), SLOT_STORY_BANNER
            ),
        )
        self.assertEqual(authorized.accessor, "storage")
        self.assertEqual(authorized.ref, "catalog/art-1/story_banner.png")
        self.assertEqual(authorized.expected_digest, "1" * 64)
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_A,
                placement=catalog_placement(
                    self.repository.get_catalog_asset("art-1"),
                    SLOT_EXPERIENCE_SUPPORT,
                ),
            )
        )
        self.assertIsNone(
            self.repository.get_media_authorization(
                owner_id=OWNER_A,
                placement=catalog_placement(
                    self.repository.get_catalog_asset("art-1"),
                    SLOT_STORY_BANNER,
                    version=9,
                ),
            )
        )


class CursorSnapshotFenceTests(unittest.TestCase):
    """The keyset cursor is fenced to one exact catalog generation."""

    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        for index in range(5):
            self.repository.seed_catalog_asset(
                asset_id="art-page-%02d" % index,
                label="page item %02d" % index,
                category="Paged",
                tags=("page",),
                digest=sha256_hex("page-%d" % index),
            )

    def test_insertion_between_pages_requires_a_restart(self):
        first = self.repository.list_catalog(query="page", limit=2)
        self.assertIsNotNone(first.next_cursor)
        self.assertEqual(len(first.items), 2)
        self.repository.seed_catalog_asset(
            asset_id="art-page-aa",
            label="page item 0a",
            category="Paged",
            tags=("page",),
            digest=sha256_hex("page-inserted"),
        )
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.list_catalog(
                query="page", limit=2, cursor=first.next_cursor
            )
        self.assertEqual(caught.exception.code, "catalog-changed")

    def test_withdrawal_between_pages_requires_a_restart(self):
        first = self.repository.list_catalog(query="page", limit=2)
        self.repository.set_catalog_lifecycle(
            asset_id="art-page-04", version=1, lifecycle=LIFECYCLE_WITHDRAWN
        )
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.list_catalog(
                query="page", limit=2, cursor=first.next_cursor
            )
        self.assertEqual(caught.exception.code, "catalog-changed")

    def test_untouched_generation_pages_completely_without_duplicates(self):
        seen, cursor, pages = [], None, 0
        while True:
            page = self.repository.list_catalog(query="page", limit=2, cursor=cursor)
            seen.extend(item.asset_id for item in page.items)
            pages += 1
            cursor = page.next_cursor
            if cursor is None:
                break
        self.assertEqual(pages, 3)
        self.assertEqual(len(seen), len(set(seen)))
        self.assertEqual(sorted(seen), sorted("art-page-%02d" % i for i in range(5)))


class OwnerPhotoCompareAndSetTests(unittest.TestCase):
    """Mirrored Photo Capture rows are created once and updated compare-and-set."""

    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.record = self.repository.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-1",
            digest="a" * 64,
            width=1200,
            height=800,
            version=1,
            version_token="0000000000000002",
        )

    def test_create_refuses_an_existing_source(self):
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.create_owner_photo(self.record)
        self.assertEqual(caught.exception.code, "source-exists")
        self.assertEqual(self.repository.get_owner_photo(OWNER_A, "source-1"), self.record)

    def test_update_requires_the_exact_prior_identity(self):
        candidate = replace(
            self.record, version=2, version_token="0000000000000003", digest="b" * 64
        )
        for expected_version, expected_token in ((1, "0000000000000009"), (7, "0000000000000002")):
            with self.subTest(expected_version=expected_version):
                before = self.repository.snapshot()
                with self.assertRaises(ResumeMediaRepositoryError) as caught:
                    self.repository.update_owner_photo_state(
                        owner_id=OWNER_A,
                        source_id="source-1",
                        record=candidate,
                        expected_lifecycle=LIFECYCLE_ACTIVE,
                        expected_version=expected_version,
                        expected_version_token=expected_token,
                    )
                self.assertEqual(caught.exception.code, "source-changed")
                self.assertEqual(self.repository.snapshot(), before)
        stored = self.repository.update_owner_photo_state(
            owner_id=OWNER_A,
            source_id="source-1",
            record=candidate,
            expected_lifecycle=LIFECYCLE_ACTIVE,
            expected_version=1,
            expected_version_token="0000000000000002",
        )
        self.assertEqual(stored.version, 2)
        self.assertEqual(self.repository.get_owner_photo(OWNER_A, "source-1"), candidate)

    def test_update_is_keyed_by_the_requested_identity_not_the_record(self):
        """A provider row for another source can never update this source."""

        other = self.repository.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-2",
            digest="c" * 64,
            width=1200,
            height=800,
            version=1,
            version_token="0000000000000002",
        )
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.update_owner_photo_state(
                owner_id=OWNER_A,
                source_id="source-1",
                record=replace(other, digest="d" * 64),
                expected_lifecycle=LIFECYCLE_ACTIVE,
                expected_version=1,
                expected_version_token="0000000000000002",
            )
        self.assertEqual(caught.exception.code, "source-changed")
        self.assertEqual(self.repository.snapshot(), before)
        self.assertEqual(self.repository.get_owner_photo(OWNER_A, "source-2"), other)

    def test_update_never_resurrects_a_non_active_source(self):
        candidate = replace(
            self.record, version=9, version_token="0000000000000009", digest="b" * 64
        )
        for lifecycle, code in (
            (LIFECYCLE_DELETED, "source-deleted"),
            (LIFECYCLE_RESTRICTED, "source-restricted"),
            (LIFECYCLE_WITHDRAWN, "source-withdrawn"),
        ):
            with self.subTest(lifecycle=lifecycle):
                self.repository.update_owner_photo(
                    owner_id=OWNER_A, source_id="source-1", lifecycle=lifecycle
                )
                before = self.repository.snapshot()
                with self.assertRaises(ResumeMediaRepositoryError) as caught:
                    self.repository.update_owner_photo_state(
                        owner_id=OWNER_A,
                        source_id="source-1",
                        record=candidate,
                        expected_lifecycle=LIFECYCLE_ACTIVE,
                        expected_version=1,
                        expected_version_token="0000000000000002",
                    )
                self.assertEqual(caught.exception.code, code)
                self.assertEqual(self.repository.snapshot(), before)
                self.assertEqual(
                    self.repository.get_owner_photo(OWNER_A, "source-1").lifecycle,
                    lifecycle,
                )


class CommitRevalidationTests(unittest.TestCase):
    """Every persisted placement is validated inside the atomic commit."""

    def setUp(self):
        self.repository = InMemoryResumeMediaRepository()
        self.art = self.repository.seed_catalog_asset(
            asset_id="art-1",
            label="Quiet Forest",
            category="Nature",
            digest="a" * 64,
            derivatives=(
                {
                    "slot": SLOT_STORY_BANNER,
                    "ref": "catalog/art-1/story_banner.png",
                    "digest": "1" * 64,
                    "byte_length": 5,
                },
            ),
        )
        self.photo = self.repository.seed_owner_photo(
            owner_id=OWNER_A,
            source_id="source-1",
            digest="b" * 64,
            width=1200,
            height=800,
            version=1,
        )

    def assert_refused_without_mutation(self, code, *, operation, **kwargs):
        draft_before = self.repository.get_draft(OWNER_A)
        publication_before = self.repository.get_publication(OWNER_A)
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            operation(**kwargs)
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(self.repository.get_draft(OWNER_A), draft_before)
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        for command in (COMMAND_ADD_MEDIA, COMMAND_KEEP_WORDS_ONLY, COMMAND_PUBLISH):
            for request_uuid in ("req-1", "req-9", "draft-1", "pub-1"):
                self.assertIsNone(
                    self.repository.get_receipt(
                        owner_id=OWNER_A,
                        command_type=command,
                        request_uuid=request_uuid,
                    )
                )

    def test_draft_commit_refuses_a_withdrawn_persisted_source(self):
        self.repository.set_catalog_lifecycle(
            asset_id="art-1", version=1, lifecycle=LIFECYCLE_WITHDRAWN
        )
        self.assert_refused_without_mutation(
            "asset-withdrawn",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A),
        )
        self.assertNotIn("commit_draft", self.repository.mutation_log)

    def test_commit_refuses_a_persisted_source_that_does_not_exist(self):
        """The validated source can never differ from the persisted source."""

        ghost = MediaPlacement(
            slot=SLOT_EXPERIENCE_SUPPORT,
            source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION,
            asset_id="missing-art",
            asset_version=1,
            asset_digest="f" * 64,
            crop=ART_EXPERIENCE_CROP,
            alt_text=ALT_TEXT,
            decorative=True,
            provenance_label=provenance_label_for(
                source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION
            ),
        )
        self.assert_refused_without_mutation(
            "asset-unavailable",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=(
                catalog_placement(self.art, SLOT_STORY_BANNER),
                ghost,
            ),
            receipt=receipt(OWNER_A),
        )
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)

    def test_commit_refuses_mismatched_persisted_semantics(self):
        cases = (
            (
                "stale-digest",
                catalog_placement(
                    self.art, SLOT_STORY_BANNER, digest="0" * 64
                ),
            ),
            (
                # A catalog revision is addressed by exact version, so an
                # unknown revision is an unavailable asset.
                "asset-unavailable",
                catalog_placement(self.art, SLOT_STORY_BANNER, version=4),
            ),
            (
                "stale-version",
                photo_placement(self.photo, SLOT_STORY_BANNER, version=7),
            ),
            (
                "crop-slot-mismatch",
                catalog_placement(
                    self.art, SLOT_STORY_BANNER, crop=ART_EXPERIENCE_CROP
                ),
            ),
            (
                "invalid-provenance",
                catalog_placement(
                    self.art,
                    SLOT_STORY_BANNER,
                    provenance_label="Generated illustration (private-locator)",
                ),
            ),
            (
                "required",
                catalog_placement(
                    self.art,
                    SLOT_STORY_BANNER,
                    alt_text="",
                    decorative=False,
                ),
            ),
            (
                "invalid-presentation-version",
                catalog_placement(
                    self.art, SLOT_STORY_BANNER, presentation_version=0
                ),
            ),
            (
                "invalid-caption",
                catalog_placement(
                    self.art, SLOT_STORY_BANNER, caption="x" * 501
                ),
            ),
        )
        for index, (code, placement) in enumerate(cases):
            with self.subTest(code=code):
                self.assert_refused_without_mutation(
                    code,
                    operation=self.repository.commit_draft,
                    owner_id=OWNER_A,
                    expected_version=0,
                    placements=(placement,),
                    receipt=receipt(OWNER_A, uuid="req-%d" % index),
                )
                self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)

    def test_commit_refuses_duplicate_or_unknown_slots(self):
        duplicate = (
            catalog_placement(self.art, SLOT_STORY_BANNER),
            catalog_placement(self.art, SLOT_STORY_BANNER, alt_text="Second"),
        )
        self.assert_refused_without_mutation(
            "duplicate-slot",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=duplicate,
            receipt=receipt(OWNER_A),
        )
        unknown = catalog_placement(self.art, SLOT_STORY_BANNER)
        object.__setattr__(unknown, "slot", "hero_banner")
        self.assert_refused_without_mutation(
            "invalid-slot",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=(unknown,),
            receipt=receipt(OWNER_A),
        )
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)

    def test_draft_commit_refuses_a_non_ready_persisted_source(self):
        self.repository.update_owner_photo(
            owner_id=OWNER_A, source_id="source-1", state=READINESS_FAILED
        )
        self.assert_refused_without_mutation(
            "source-failed",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=(photo_placement(self.photo, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A),
        )
        self.repository.update_owner_photo(
            owner_id=OWNER_A, source_id="source-1", state=READINESS_READY
        )

    def test_draft_commit_refuses_an_out_of_shape_persisted_crop(self):
        self.assert_refused_without_mutation(
            "crop-slot-mismatch",
            operation=self.repository.commit_draft,
            owner_id=OWNER_A,
            expected_version=0,
            placements=(
                photo_placement(
                    self.photo,
                    SLOT_EXPERIENCE_SUPPORT,
                    crop=PHOTO_BANNER_CROP,
                ),
            ),
            receipt=receipt(OWNER_A),
        )

    def test_draft_commit_detects_a_version_change_injected_on_entry(self):
        def racing_entry(operation):
            if operation == "commit_draft":
                self.repository.update_owner_photo(
                    owner_id=OWNER_A,
                    source_id="source-1",
                    version=2,
                    digest="c" * 64,
                )

        self.repository.on_commit_entry = racing_entry
        before = self.repository.snapshot()
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_draft(
                owner_id=OWNER_A,
                expected_version=0,
                placements=(photo_placement(self.photo, SLOT_STORY_BANNER),),
                receipt=receipt(OWNER_A),
            )
        self.assertEqual(caught.exception.code, "stale-version")
        self.assertEqual(self.repository.get_draft(OWNER_A).version, 0)
        self.assertEqual(
            self.repository.get_owner_photo(OWNER_A, "source-1").version, 2
        )
        self.assertNotEqual(self.repository.snapshot(), before)

    def test_publication_commit_detects_a_race_injected_on_entry(self):
        self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A, uuid="draft-1"),
        )
        draft_before = self.repository.get_draft(OWNER_A)
        publication_before = self.repository.get_publication(OWNER_A)

        def racing_entry(operation):
            if operation == "commit_publication":
                self.repository.set_catalog_lifecycle(
                    asset_id="art-1", version=1, lifecycle=LIFECYCLE_WITHDRAWN
                )

        self.repository.on_commit_entry = racing_entry
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_publication(
                owner_id=OWNER_A,
                expected_draft_version=1,
                expected_publication_version=0,
                placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
                digest="p" * 64,
                receipt=receipt(OWNER_A, command=COMMAND_PUBLISH, uuid="pub-1"),
            )
        self.assertEqual(caught.exception.code, "asset-withdrawn")
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        self.assertEqual(self.repository.get_draft(OWNER_A), draft_before)
        self.assertNotIn("commit_publication", self.repository.mutation_log)
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_A, command_type=COMMAND_PUBLISH, request_uuid="pub-1"
            )
        )
        self.assertEqual(
            self.repository.get_catalog_asset("art-1").lifecycle, LIFECYCLE_WITHDRAWN
        )

    def test_publication_commit_refuses_a_persisted_missing_source(self):
        self.repository.commit_draft(
            owner_id=OWNER_A,
            expected_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            receipt=receipt(OWNER_A, uuid="draft-1"),
        )
        first = self.repository.commit_publication(
            owner_id=OWNER_A,
            expected_draft_version=1,
            expected_publication_version=0,
            placements=(catalog_placement(self.art, SLOT_STORY_BANNER),),
            digest="p" * 64,
            receipt=receipt(OWNER_A, command=COMMAND_PUBLISH, uuid="pub-1"),
        )
        self.assertEqual(first.version, 1)
        ghost = MediaPlacement(
            slot=SLOT_STORY_BANNER,
            source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION,
            asset_id="missing-art",
            asset_version=1,
            asset_digest="f" * 64,
            crop=ART_BANNER_CROP,
            alt_text=ALT_TEXT,
            decorative=True,
            provenance_label=provenance_label_for(
                source_kind=SOURCE_KIND_GENERATED_ILLUSTRATION
            ),
        )
        publication_before = self.repository.get_publication(OWNER_A)
        with self.assertRaises(ResumeMediaRepositoryError) as caught:
            self.repository.commit_publication(
                owner_id=OWNER_A,
                expected_draft_version=1,
                expected_publication_version=1,
                placements=(ghost,),
                digest="q" * 64,
                receipt=receipt(OWNER_A, command=COMMAND_PUBLISH, uuid="pub-2"),
            )
        self.assertEqual(caught.exception.code, "asset-unavailable")
        self.assertEqual(self.repository.get_publication(OWNER_A), publication_before)
        self.assertEqual(self.repository.get_publication(OWNER_A).version, 1)
        self.assertIsNone(
            self.repository.get_receipt(
                owner_id=OWNER_A, command_type=COMMAND_PUBLISH, request_uuid="pub-2"
            )
        )


class MetadataSafetyTests(unittest.TestCase):
    """Persisted catalog metadata is deep-frozen and projected by allowlist."""

    def test_nested_metadata_is_deep_frozen_and_allowlisted(self):
        repository = InMemoryResumeMediaRepository()
        provenance = {
            "model": "synthetic-art-v1",
            "created_utc": "2026-01-01T00:00:00Z",
            "provider_locator": "https://private.example/asset/1",
            "storage_key": "secret-storage-key",
            "prompt": "internal generation prompt",
            "nested": {"locator": "deep-private-locator"},
        }
        rights = {
            "rights_id": "rights-1",
            "approval_state": "approved",
            "internal_notes": "private reviewer note",
        }
        repository.seed_catalog_asset(
            asset_id="art-1",
            label="Quiet Forest",
            category="Nature",
            digest="a" * 64,
            provenance=provenance,
            rights=rights,
        )
        provenance["model"] = "mutated-after-seed"
        rights["rights_id"] = "mutated-after-seed"
        stored = repository.get_catalog_asset("art-1")
        self.assertEqual(
            catalog_provenance_view(stored),
            {"model": "synthetic-art-v1", "created_utc": "2026-01-01T00:00:00Z"},
        )
        self.assertEqual(
            catalog_rights_view(stored),
            {"rights_id": "rights-1", "approval_state": "approved"},
        )
        with self.assertRaises(TypeError):
            stored.provenance["model"] = "tampered"
        serialized = canonical_json(
            {
                "provenance": catalog_provenance_view(stored),
                "rights": catalog_rights_view(stored),
            }
        )
        for private in (
            "private.example",
            "secret-storage-key",
            "internal generation prompt",
            "internal_notes",
            "deep-private-locator",
            "mutated-after-seed",
        ):
            self.assertNotIn(private, serialized)


if __name__ == "__main__":
    unittest.main()

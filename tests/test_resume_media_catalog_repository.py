"""Durable catalog fence. Fixtures are not authority."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from services.resume_media_catalog_repository import (
    CatalogFenceDenied,
    CatalogFenceUnavailable,
    InMemoryResumeCatalogRepository,
    SqlResumeCatalogRepository,
)
from services.resume_media_repository import CatalogAssetRecord


def record(lifecycle="active"):
    return CatalogAssetRecord(
        "asset-1",
        2,
        "a" * 64,
        "Leadership",
        "concept",
        ("Teamwork",),
        1600,
        900,
        lifecycle=lifecycle,
    )


class ResumeMediaCatalogRepositoryTests(unittest.TestCase):
    def test_withdraw_is_synchronous_and_get_active_fails_closed(self):
        catalog = InMemoryResumeCatalogRepository()
        catalog.put(record())
        self.assertEqual(catalog.get_active("asset-1", 2).lifecycle, "active")
        catalog.withdraw("asset-1", 2)
        with self.assertRaises(CatalogFenceDenied):
            catalog.get_active("asset-1", 2)

    def test_missing_and_inactive_records_are_denied(self):
        catalog = InMemoryResumeCatalogRepository()
        with self.assertRaises(CatalogFenceDenied):
            catalog.get_active("missing", 1)
        catalog.put(record(lifecycle="withdrawn"))
        with self.assertRaises(CatalogFenceDenied):
            catalog.get_active("asset-1", 2)

    def test_sql_adapter_maps_active_rows_and_unavailable_errors(self):
        database = MagicMock()
        database.first_row.return_value = {
            "asset_id": "asset-1",
            "version": 2,
            "digest": "a" * 64,
            "label": "Leadership",
            "category": "concept",
            "tags": "Teamwork|Quiet",
            "width": 1600,
            "height": 900,
            "origin": "generated_illustration",
            "lifecycle": "active",
        }
        mapped = SqlResumeCatalogRepository(database).get_active("asset-1", 2)
        self.assertEqual(mapped.tags, ("Teamwork", "Quiet"))
        database.first_row.return_value = {"lifecycle": "withdrawn"}
        with self.assertRaises(CatalogFenceDenied):
            SqlResumeCatalogRepository(database).get_active("asset-1", 2)
        database.first_row.side_effect = ValueError("down")
        with self.assertRaises(CatalogFenceUnavailable):
            SqlResumeCatalogRepository(database).get_active("asset-1", 2)


if __name__ == "__main__":
    unittest.main()

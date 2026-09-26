"""Durable curated-catalog fence for generated Resume media.

Fixtures cannot stand in for this authority. Withdrawal is synchronous.
"""

from __future__ import annotations

import copy
from dataclasses import replace
from typing import Any

from services.database_service import DatabaseServiceError, database_service
from services.resume_media_repository import CatalogAssetRecord


class CatalogFenceUnavailable(RuntimeError):
    """Raised when the catalog authority cannot be read or mutated."""


class CatalogFenceDenied(RuntimeError):
    """Raised when a catalog asset is withdrawn, missing, or inactive."""


class InMemoryResumeCatalogRepository:
    def __init__(self) -> None:
        self._assets: dict[tuple[str, int], dict[str, Any]] = {}

    def put(self, record: CatalogAssetRecord) -> None:
        if type(record) is not CatalogAssetRecord:
            raise CatalogFenceUnavailable("Catalog storage is unavailable.")
        self._assets[(record.asset_id, record.version)] = {
            "record": record,
            "lifecycle": record.lifecycle,
        }

    def get_active(self, asset_id: str, version: int) -> CatalogAssetRecord:
        row = self._assets.get((asset_id, version))
        if row is None or row["lifecycle"] != "active":
            raise CatalogFenceDenied("Catalog asset is unavailable.")
        record = row["record"]
        if record.lifecycle != "active":
            raise CatalogFenceDenied("Catalog asset is unavailable.")
        return record

    def withdraw(self, asset_id: str, version: int) -> None:
        row = self._assets.get((asset_id, version))
        if row is None:
            raise CatalogFenceDenied("Catalog asset is unavailable.")
        record = row["record"]
        withdrawn = replace(record, lifecycle="withdrawn")
        self._assets[(asset_id, version)] = {"record": withdrawn, "lifecycle": "withdrawn"}


class SqlResumeCatalogRepository:
    def __init__(self, database=None) -> None:
        self.database = database or database_service

    def get_active(self, asset_id: str, version: int) -> CatalogAssetRecord:
        try:
            row = self.database.first_row(
                "usp_GetResumeCatalogAsset",
                [("@AssetId", asset_id), ("@AssetVersion", version)],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise CatalogFenceUnavailable("Catalog storage is unavailable.") from error
        if not row or row.get("lifecycle") != "active":
            raise CatalogFenceDenied("Catalog asset is unavailable.")
        tags = row.get("tags") or ()
        if type(tags) is str:
            tags = tuple(item for item in tags.split("|") if item)
        provenance = row.get("provenance") or ()
        return CatalogAssetRecord(
            asset_id=str(row["asset_id"]),
            version=int(row["version"]),
            digest=str(row["digest"]),
            label=str(row["label"]),
            category=str(row.get("category") or "library"),
            tags=tuple(tags),
            width=int(row["width"]),
            height=int(row["height"]),
            origin=str(row["origin"]),
            provenance=tuple(provenance),
            lifecycle=str(row["lifecycle"]),
        )

    def withdraw(self, owner_user_key: str, request_id: str, asset_id: str, version: int) -> dict[str, Any]:
        try:
            row = self.database.last_row(
                "usp_CommitResumeCatalogCommandForOwner",
                [
                    ("@UserKey", owner_user_key),
                    ("@RequestId", request_id),
                    ("@CommandJson", {"type": "withdraw", "asset_id": asset_id, "version": version}),
                ],
            )
        except (DatabaseServiceError, ValueError) as error:
            raise CatalogFenceUnavailable("Catalog storage is unavailable.") from error
        if not row:
            raise CatalogFenceUnavailable("Catalog storage is unavailable.")
        return dict(row)

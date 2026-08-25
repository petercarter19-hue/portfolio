"""One provider-neutral, fixture-safe shared-source ingestion path."""

from __future__ import annotations

from datetime import datetime

from .canonical_service import CanonicalService, MyOpportunitiesCanonicalError, SourceListing
from .connectors import SourceConnector


class IngestionService:
    """Coordinate connector output without allowing a connector to write truth.

    ``SourceConnector`` has exactly three read-only operations.  This service
    alone records a receipt and asks the canonical service to admit its
    normalized candidate, so every source gets the same policy/version/dedupe
    checks.  It deliberately has no scheduler or network configuration.
    """

    def __init__(self, canonical: CanonicalService) -> None:
        self._canonical = canonical

    def register(self, connector: SourceConnector, *, now: datetime) -> None:
        self._canonical.register_connector(connector.describe(), now=now)

    def ingest(self, connector: SourceConnector, *, now: datetime) -> tuple[SourceListing, ...]:
        descriptor = connector.describe()
        accepted: list[SourceListing] = []
        for raw_receipt in connector.acquire():
            candidate = connector.normalize(raw_receipt)
            # Normalize and class-check before a receipt body becomes retained
            # source history. The canonical aggregate then persists and links
            # receipt/version atomically, including duplicate observations.
            accepted.append(
                self._canonical.admit_observation(descriptor, raw_receipt, candidate, now=now)
            )
        return tuple(accepted)


__all__ = ["IngestionService", "MyOpportunitiesCanonicalError"]

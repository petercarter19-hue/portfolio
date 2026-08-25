from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from services.my_opportunities.canonical_service import CanonicalService, InMemoryCanonicalRepository, LiveOpportunityGateConfig, MyOpportunitiesCanonicalError, SourcePolicy
from services.my_opportunities.connectors import ConnectorDescriptor, NormalizedListing, SourceReceiptInput, SyntheticConnector
from services.my_opportunities.ingestion_service import IngestionService


ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 8, 24, 12, tzinfo=timezone.utc)
DIMENSIONS = {key: True for key in ("display", "excerpt", "full_description", "storage", "ai_ml_use", "caching", "retention", "attribution", "removal", "termination", "exit", "survivable_minimal_facts")}
ACTIONS = frozenset({"register", "acquire", "persist", "display", "retain", "remove", "terminate", "export", "ai", "cache"})


def build_policy(descriptor, *, actions=ACTIONS):
    return SourcePolicy(descriptor.policy_key, descriptor.policy_version, descriptor.source_id, descriptor.data_class, actions, 1, NOW - timedelta(days=1), None, DIMENSIONS, "fixture-evidence", "fixture-decision")


class IngestionTests(unittest.TestCase):
    def _fixture_connector(self):
        document = json.loads((ROOT / "tests/fixtures/my_opportunities/c2_synthetic_feed.json").read_text())
        descriptor = ConnectorDescriptor(
            capabilities=frozenset(document["descriptor"]["capabilities"]),
            schedule_hints=tuple(document["descriptor"]["schedule_hints"]),
            **{key: value for key, value in document["descriptor"].items() if key not in {"capabilities", "schedule_hints"}},
        )
        rows = []
        for row in document["rows"]:
            normalized = NormalizedListing(
                locations=tuple(row["locations"]), expected_application_hosts=tuple(row["expected_application_hosts"]),
                requirement_clauses=tuple(row["requirement_clauses"]), data_class=descriptor.data_class,
                **{key: value for key, value in row.items() if key not in {"locations", "expected_application_hosts", "requirement_clauses"}},
            )
            receipt = SourceReceiptInput(row["external_reference"], NOW, "application/json", json.dumps(row, sort_keys=True).encode())
            rows.append((receipt, normalized))
        return descriptor, SyntheticConnector(descriptor, rows)

    def _services(self):
        repository = InMemoryCanonicalRepository()
        canonical = CanonicalService(repository, LiveOpportunityGateConfig(timedelta(days=7), timedelta(days=2)))
        return repository, canonical, IngestionService(canonical)

    def test_synthetic_connector_is_provider_neutral_and_cannot_be_production(self):
        descriptor, connector = self._fixture_connector()
        self.assertEqual(descriptor.data_class, "fixture")
        self.assertEqual(tuple(connector.acquire())[0].external_reference, "astraeus-platform-1")
        with self.assertRaises(ValueError):
            SyntheticConnector(
                ConnectorDescriptor("bad", "licensed", "bad-policy", 1, frozenset(), (), "US", "synthetic", "production"),
                (),
            )

    def test_registration_and_ingestion_apply_policy_before_every_write(self):
        repository, canonical, ingestion = self._services()
        descriptor, connector = self._fixture_connector()
        canonical.register_policy(build_policy(descriptor), now=NOW)
        ingestion.register(connector, now=NOW)
        listings = ingestion.ingest(connector, now=NOW)
        self.assertEqual(len(listings), 1)
        self.assertEqual(listings[0].state, "current")
        self.assertEqual(repository.versions_for_listing(listings[0].listing_key)[0].employer, "Astraeus")

        receipt_count = len(repository._receipts)
        listings_again = ingestion.ingest(connector, now=NOW + timedelta(minutes=1))
        self.assertEqual(listings_again[0].listing_key, listings[0].listing_key)
        self.assertEqual(len(repository.versions_for_listing(listings[0].listing_key)), 1)
        self.assertEqual(len(repository._receipts), receipt_count + 1, "every observed payload is an immutable receipt")
        version = repository.versions_for_listing(listings[0].listing_key)[0]
        self.assertEqual(
            set(repository.receipt_keys_for_version(version.version_key)),
            set(repository._receipts),
            "every retained duplicate observation is linked to its source version",
        )

    def test_connector_cannot_write_canonical_truth_without_registered_descriptor(self):
        _repository, canonical, ingestion = self._services()
        descriptor, connector = self._fixture_connector()
        canonical.register_policy(build_policy(descriptor), now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "connector_unregistered"):
            ingestion.ingest(connector, now=NOW)

    def test_malformed_or_cross_class_candidate_is_quarantined_before_source_version(self):
        _repository, canonical, ingestion = self._services()
        descriptor, _connector = self._fixture_connector()
        canonical.register_policy(build_policy(descriptor), now=NOW)
        canonical.register_connector(descriptor, now=NOW)
        malformed = NormalizedListing("bad", "Astraeus", "", ("Chicago",), None, "https://jobs.example/1", ("jobs.example",), "", (), {}, "fixture")
        raw = SourceReceiptInput("bad", NOW, "application/json", b"{}")
        receipt = canonical.record_receipt(descriptor, raw, now=NOW)
        with self.assertRaisesRegex(MyOpportunitiesCanonicalError, "admission_refused"):
            canonical.admit(descriptor, receipt, malformed, now=NOW)
        self.assertEqual(tuple(_repository._versions.values()), ())
        self.assertEqual(tuple(_repository._receipts.values()), (), "rejected observations retain no orphan body")


if __name__ == "__main__":
    unittest.main()

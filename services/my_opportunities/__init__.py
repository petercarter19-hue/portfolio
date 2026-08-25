"""Fixture-only canonical foundation for My Opportunities.

This package deliberately has no route registration, provider configuration, or
database-service import.  Later packages may inject a SQL repository only after
their own protected activation; C2 keeps the canonical rules independently
testable with synthetic data.
"""

from .canonical_service import (
    CanonicalService,
    InMemoryCanonicalRepository,
    LiveOpportunityGateConfig,
    SourcePolicy,
)

__all__ = [
    "CanonicalService",
    "InMemoryCanonicalRepository",
    "LiveOpportunityGateConfig",
    "SourcePolicy",
]

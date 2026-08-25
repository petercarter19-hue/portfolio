"""Provider-neutral connector shapes and the synthetic C2 connector only."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Protocol


@dataclass(frozen=True)
class ConnectorDescriptor:
    source_id: str
    source_class: str
    policy_key: str
    policy_version: int
    capabilities: frozenset[str]
    schedule_hints: tuple[str, ...]
    territory: str
    product: str
    data_class: str


@dataclass(frozen=True)
class SourceReceiptInput:
    external_reference: str
    received_at: datetime
    content_type: str
    payload: bytes


@dataclass(frozen=True)
class NormalizedListing:
    external_reference: str
    employer: str
    title: str
    locations: tuple[str, ...]
    arrangement: str | None
    application_url: str
    expected_application_hosts: tuple[str, ...]
    description: str
    requirement_clauses: tuple[str, ...]
    fields: dict[str, str]
    data_class: str


class SourceConnector(Protocol):
    def describe(self) -> ConnectorDescriptor: ...

    def acquire(self) -> Iterable[SourceReceiptInput]: ...

    def normalize(self, receipt: SourceReceiptInput) -> NormalizedListing: ...


class SyntheticConnector:
    """A deterministic fixture connector; it has no network or credentials."""

    def __init__(
        self, descriptor: ConnectorDescriptor, rows: Iterable[tuple[SourceReceiptInput, NormalizedListing]]
    ) -> None:
        if descriptor.data_class != "fixture":
            raise ValueError("The C2 synthetic connector is fixture-only.")
        self._descriptor = descriptor
        self._rows = tuple(rows)
        self._normalized = {id(receipt): listing for receipt, listing in self._rows}

    def describe(self) -> ConnectorDescriptor:
        return self._descriptor

    def acquire(self) -> Iterable[SourceReceiptInput]:
        return tuple(receipt for receipt, _ in self._rows)

    def normalize(self, receipt: SourceReceiptInput) -> NormalizedListing:
        try:
            return self._normalized[id(receipt)]
        except KeyError as error:
            raise ValueError("Synthetic receipt is not owned by this connector.") from error

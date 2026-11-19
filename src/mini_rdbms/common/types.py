"""Shared data types and structural interfaces for engine components."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Iterator, Protocol, Sequence, Union

Value = Union[int, float, str, bool, None]
Row = Dict[str, Value]
RecordId = int


class DataType(str, Enum):
    """SQL scalar types supported by the initial engine."""

    INT = "INT"
    FLOAT = "FLOAT"
    TEXT = "TEXT"
    BOOL = "BOOL"


@dataclass(frozen=True)
class ColumnSchema:
    """Describe one table column and its integrity constraints."""

    name: str
    data_type: DataType
    nullable: bool = True
    primary_key: bool = False


@dataclass(frozen=True)
class IndexSchema:
    """Describe an index declared on one table column."""

    name: str
    table_name: str
    column_name: str
    index_type: str


@dataclass(frozen=True)
class TableSchema:
    """Immutable schema metadata used by semantic and storage layers."""

    name: str
    columns: tuple[ColumnSchema, ...]

    def get_column(self, name: str) -> ColumnSchema | None:
        """Find a column by exact name."""
        return next((column for column in self.columns if column.name == name), None)

    def has_column(self, name: str) -> bool:
        """Return whether this table defines the requested column."""
        return self.get_column(name) is not None

    @property
    def primary_key(self) -> ColumnSchema | None:
        """Return the primary-key column, if one is defined."""
        return next((column for column in self.columns if column.primary_key), None)


class Catalog(Protocol):
    """Read-only catalog contract used by semantic validation."""

    def get_table(self, name: str) -> TableSchema | None:
        """Return table metadata or None when the table is unknown."""

    def get_index(self, name: str) -> IndexSchema | None:
        """Return index metadata or None when the index is unknown."""

    def list_tables(self) -> Sequence[TableSchema]:
        """Return known table schemas."""


class TableStorage(Protocol):
    """Minimal table-storage contract needed by future execution layers."""

    def insert(self, row: Row) -> RecordId:
        """Store a row and return its record identifier."""

    def fetch(self, record_id: RecordId) -> Row | None:
        """Fetch one row by record identifier."""

    def scan(self) -> Iterator[tuple[RecordId, Row]]:
        """Yield stored records in stable order."""

    def update(self, record_id: RecordId, row: Row) -> None:
        """Replace one stored row."""

    def delete(self, record_id: RecordId) -> None:
        """Delete one stored row."""

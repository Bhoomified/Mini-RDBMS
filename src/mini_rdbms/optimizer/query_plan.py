"""Logical access plans selected for parsed statements."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mini_rdbms.common.types import RecordId


class AccessPath(str, Enum):
    FULL_SCAN = "FULL_SCAN"
    HASH_LOOKUP = "HASH_LOOKUP"
    BTREE_LOOKUP = "BTREE_LOOKUP"
    BTREE_RANGE = "BTREE_RANGE"


@dataclass(frozen=True)
class QueryPlan:
    """Chosen access path and the reason it was selected."""

    access_path: AccessPath
    table: str
    index_name: str | None
    reason: str


@dataclass(frozen=True)
class ExecutionResult:
    """Rows and candidate record IDs produced by an executor."""

    rows: list[dict]
    record_ids: set[RecordId]

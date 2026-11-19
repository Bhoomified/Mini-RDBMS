"""Lightweight runtime statistics used by the rule-based planner."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableStatistics:
    """Observed row and distinct-value counts for one table."""

    row_count: int
    distinct_values: dict[str, int]

    @classmethod
    def from_rows(cls, rows) -> "TableStatistics":
        materialized = list(rows)
        columns = set().union(*(row.keys() for row in materialized)) if materialized else set()
        return cls(
            len(materialized),
            {column: len({row.get(column) for row in materialized}) for column in columns},
        )

    def equality_selectivity(self, column: str) -> float:
        """Estimate equality selectivity from observed distinct values."""
        distinct = self.distinct_values.get(column, 0)
        return 1.0 if distinct == 0 else 1.0 / distinct

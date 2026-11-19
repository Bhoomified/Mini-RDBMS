"""Correct row execution for planned SELECT access paths."""

from __future__ import annotations

from .query_plan import ExecutionResult, QueryPlan


class Executor:
    """Execute a plan over a storage facade and optional index registry."""

    def __init__(self, storage, indexes) -> None:
        self.storage = storage
        self.indexes = indexes

    def select(self, statement, plan: QueryPlan) -> ExecutionResult:
        candidates = self.candidate_ids(statement, plan)
        if candidates is not None:
            records = (
                (record_id, self.storage.fetch(statement.table, record_id))
                for record_id in candidates
            )
        else:
            records = iter(self.storage.scan(statement.table))
        rows = []
        record_ids = set()
        for record_id, row in records:
            if row is None:
                continue
            if self._matches(row, statement.conditions):
                record_ids.add(record_id)
                rows.append(row if statement.columns == ("*",) else {
                    column: row[column] for column in statement.columns
                })
        return ExecutionResult(rows, record_ids)

    def candidate_ids(self, statement, plan: QueryPlan) -> set[int] | None:
        """Return index candidates, or None when a full scan is required."""
        candidates = None
        index = self.indexes.get(plan.index_name) if plan.index_name else None
        condition = next(
            (item for item in statement.conditions if index and item.column == self.indexes.column(plan.index_name)),
            None,
        )
        if condition and index:
            if plan.access_path.value == "HASH_LOOKUP":
                candidates = index.search(condition.value)
            elif plan.access_path.value == "BTREE_LOOKUP":
                candidates = index.search(condition.value)
            elif plan.access_path.value == "BTREE_RANGE":
                candidates = index.range_search(
                    lower=condition.value if condition.operator in {">", ">="} else None,
                    upper=condition.value if condition.operator in {"<", "<="} else None,
                    include_lower=condition.operator in {">=", "<="},
                    include_upper=condition.operator in {"<=", ">="},
                )
        return candidates

    @staticmethod
    def _matches(row, conditions):
        operations = {
            "=": lambda a, b: a == b,
            "!=": lambda a, b: a != b,
            "<>": lambda a, b: a != b,
            "<": lambda a, b: a < b,
            "<=": lambda a, b: a <= b,
            ">": lambda a, b: a > b,
            ">=": lambda a, b: a >= b,
        }
        return all(operations[item.operator](row[item.column], item.value) for item in conditions)

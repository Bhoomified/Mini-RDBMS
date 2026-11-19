"""Simple rule-based access-path planner."""

from __future__ import annotations

from mini_rdbms.parser.ast_nodes import Condition, SelectStatement

from .query_plan import AccessPath, QueryPlan


class Planner:
    """Choose an available index for a single-table WHERE predicate."""

    def __init__(self, catalog, storage=None, index_manager=None) -> None:
        self.catalog = catalog
        self.storage = storage
        self.index_manager = index_manager

    def plan(self, statement: SelectStatement) -> QueryPlan:
        indexes = [
            index
            for index in self.catalog.list_indexes()
            if index.table_name == statement.table
        ]
        statistics = None
        if self.storage is not None:
            from .statistics import TableStatistics

            statistics = TableStatistics.from_rows(
                row for _record_id, row in self.storage.scan(statement.table)
            )
        candidates = []
        for condition in statement.conditions:
            for index in indexes:
                if index.column_name != condition.column:
                    continue
                if index.index_type == "HASH" and condition.operator == "=":
                    candidates.append(
                        (
                            self._estimate(index.name, condition, statement),
                            QueryPlan(
                                AccessPath.HASH_LOOKUP,
                                statement.table,
                                index.name,
                                "equality predicate matches a hash index",
                            ),
                        )
                    )
                elif index.index_type == "BTREE" and condition.operator in {
                    "=", "<", "<=", ">", ">="
                }:
                    path = (
                        AccessPath.BTREE_LOOKUP
                        if condition.operator == "="
                        else AccessPath.BTREE_RANGE
                    )
                    candidates.append(
                        (
                            self._estimate(index.name, condition, statement),
                            QueryPlan(path, statement.table, index.name, "ordered index supports predicate"),
                        )
                    )
        if candidates:
            estimated, plan = min(candidates, key=lambda item: item[0])
            if statistics is not None:
                plan = QueryPlan(
                    plan.access_path,
                    plan.table,
                    plan.index_name,
                    f"{plan.reason}; estimated candidates={estimated}",
                )
            return plan
        indexed_columns = ", ".join(
            f"{index.name}({index.column_name})" for index in indexes
        )
        for condition in statement.conditions:
            if condition.operator in {"<", "<=", ">", ">="}:
                return QueryPlan(
                    AccessPath.BTREE_RANGE,
                    statement.table,
                    f"__auto_{statement.table}_{condition.column}_btree",
                    "automatic B+Tree range index will be created during execution",
                )
            if condition.operator == "=":
                return QueryPlan(
                    AccessPath.HASH_LOOKUP,
                    statement.table,
                    f"__auto_{statement.table}_{condition.column}_hash",
                    "automatic hash index will be created during execution",
                )
        detail = (
            f"available indexes: {indexed_columns}; none match the WHERE predicate"
            if indexed_columns
            else "no index is defined for this table"
        )
        return QueryPlan(
            AccessPath.FULL_SCAN,
            statement.table,
            None,
            "no applicable index was found; " + detail,
        )

    def _estimate(self, index_name: str, condition, statement: SelectStatement) -> int:
        if self.storage is None:
            return 2**31
        try:
            index = self.index_manager
            if index is None:
                return 2**31
            structure = index.get(index_name)
            if structure is None:
                return 2**31
            if condition.operator == "=":
                return len(structure.search(condition.value))
            return len(
                structure.range_search(
                    lower=condition.value if condition.operator in {">", ">="} else None,
                    upper=condition.value if condition.operator in {"<", "<="} else None,
                    include_lower=condition.operator in {">=", "<="},
                    include_upper=condition.operator in {"<=", ">="},
                )
            )
        except (AttributeError, TypeError, ValueError):
            return 2**31

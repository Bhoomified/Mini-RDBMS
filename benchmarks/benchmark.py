"""Repeatable measurements for the main query and persistence paths."""

from __future__ import annotations

import time

import os
import tempfile

from mini_rdbms.common.types import ColumnSchema, DataType, IndexSchema, TableSchema
from mini_rdbms.integration.database import Database
from mini_rdbms.integration.session import Session
from mini_rdbms.optimizer.executor import Executor
from mini_rdbms.optimizer.planner import Planner
from mini_rdbms.optimizer.query_plan import AccessPath, QueryPlan
from mini_rdbms.parser.lexer import Lexer
from mini_rdbms.parser.parser import Parser


def main() -> None:
    """Measure the main access paths over 10,000 rows."""
    database = Database()
    session = Session(database)
    session.execute("CREATE TABLE benchmark (id INT, value TEXT)")
    for record_id in range(10_000):
        database.storage.insert("benchmark", {"id": record_id, "value": "value"})
    session.execute("CREATE INDEX benchmark_hash ON benchmark (id) USING HASH")
    session.execute("CREATE INDEX benchmark_btree ON benchmark (id) USING BTREE")
    statement = Parser(Lexer("SELECT value FROM benchmark WHERE id = 9999").tokenize()).parse()
    executor = Executor(database.storage, database.indexes)
    plans = {
        "hash_equality": QueryPlan(AccessPath.HASH_LOOKUP, "benchmark", "benchmark_hash", "benchmark"),
        "btree_equality": QueryPlan(AccessPath.BTREE_LOOKUP, "benchmark", "benchmark_btree", "benchmark"),
        "btree_range": QueryPlan(AccessPath.BTREE_RANGE, "benchmark", "benchmark_btree", "benchmark"),
        "full_scan": QueryPlan(AccessPath.FULL_SCAN, "benchmark", None, "benchmark"),
    }
    queries = {
        "hash_equality": statement,
        "btree_equality": statement,
        "btree_range": Parser(
            Lexer("SELECT value FROM benchmark WHERE id >= 5000").tokenize()
        ).parse(),
        "full_scan": Parser(
            Lexer("SELECT value FROM benchmark WHERE value = 'value'").tokenize()
        ).parse(),
    }
    timings = {}
    for name, plan in plans.items():
        start = time.perf_counter()
        result = executor.select(queries[name], plan)
        timings[name] = ((time.perf_counter() - start) * 1000, len(result.rows))
    start = time.perf_counter()
    Parser(Lexer("SELECT value FROM benchmark WHERE id >= 5000").tokenize()).parse()
    parse_ms = (time.perf_counter() - start) * 1000
    start = time.perf_counter()
    Planner(database.catalog, database.storage, database.indexes).plan(queries["btree_range"])
    plan_ms = (time.perf_counter() - start) * 1000
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, "benchmark.db")
        durable = Database(path)
        durable.catalog.create_table(
            TableSchema("benchmark", (ColumnSchema("id", DataType.INT), ColumnSchema("value", DataType.TEXT)))
        )
        durable.storage.create_table(durable.catalog.get_table("benchmark"))
        for record_id in range(10_000):
            durable.storage.insert("benchmark", {"id": record_id, "value": "value"})
        start = time.perf_counter()
        durable.persist()
        persist_ms = (time.perf_counter() - start) * 1000
        start = time.perf_counter()
        Database(path)
        reopen_ms = (time.perf_counter() - start) * 1000
    print(
        f"rows=10000; parse_ms={parse_ms:.3f}; plan_ms={plan_ms:.3f}; "
        f"persist_ms={persist_ms:.3f}; reopen_ms={reopen_ms:.3f}"
    )
    for name, (elapsed, count) in timings.items():
        print(f"{name}_ms={elapsed:.3f}; rows={count}")


if __name__ == "__main__":
    main()

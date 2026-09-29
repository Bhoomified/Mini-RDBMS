"""
demo.py  -  run the optimizer on its own, with fake data (no parser/storage needed).

Run from the repo root:
    python -m engine.optimizer.demo
"""
import random
import timeit

from engine.optimizer.index import IndexManager
from engine.optimizer.planner import make_execution_plan, EQUALITY_OPS

OPS = {
    "=": lambda a, b: a == b, "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b, ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
}


def matches(row, conds):
    return all(OPS[c["op"]](row[c["column"]], c["value"]) for c in conds)


def run_plan(plan, rows_by_id, all_rows, indexes):
    """Tiny stand-in executor (the real one is Sneha's storage + Soumya's txn manager)."""
    if plan["access_path"] == "index_lookup":
        ids = indexes[plan["table"]][plan["index_column"]].lookup(plan["index_value"])
        candidates = [rows_by_id[i] for i in ids]
    else:
        candidates = all_rows
    return [r for r in candidates if matches(r, plan["residual_conditions"])]


def make_data(n=1000):
    random.seed(42)
    return [{"id": i, "name": f"student{i}", "age": random.randint(17, 30)} for i in range(1, n + 1)]


def show(title, query, schema, im, rows_by_id, rows):
    plan = make_execution_plan(query, schema, im.indexes)
    result = run_plan(plan, rows_by_id, rows, im.indexes)
    print(f"\n=== {title} ===")
    print("QUERY :", query)
    print("PLAN  :", plan)
    print("ROWS  :", len(result), "->", result[:3], "..." if len(result) > 3 else "")
    return plan


def main():
    rows = make_data(1000)
    rows_by_id = {r["id"]: r for r in rows}
    schema = {"students": {"id": "INT", "name": "TEXT", "age": "INT"}}

    im = IndexManager()
    im.create_index("students", "id", rows)      # index on id only

    q = lambda conds: {"type": "SELECT", "table": "students", "columns": ["*"], "conditions": conds}
    show("Equality on indexed column  -> index_lookup", q([{"column": "id", "op": "=", "value": 500}]), schema, im, rows_by_id, rows)
    show("Range on indexed column     -> full_scan (hash can't do >)", q([{"column": "id", "op": ">", "value": 990}]), schema, im, rows_by_id, rows)
    show("Equality on NON-indexed col -> full_scan", q([{"column": "age", "op": "=", "value": 20}]), schema, im, rows_by_id, rows)
    show("Mixed: id = 7 AND age > 18  -> index_lookup + residual filter", q([{"column": "age", "op": ">", "value": 18}, {"column": "id", "op": "=", "value": 7}]), schema, im, rows_by_id, rows)

    # correctness: both access paths must return identical rows
    conds = [{"column": "id", "op": "=", "value": 500}]
    with_idx = make_execution_plan(q(conds), schema, im.indexes)
    without = make_execution_plan(q(conds), schema, {})
    assert run_plan(with_idx, rows_by_id, rows, im.indexes) == run_plan(without, rows_by_id, rows, {})
    print("\n[OK] index_lookup and full_scan return identical rows")

    # tiny timing comparison
    t_idx = timeit.timeit(lambda: run_plan(with_idx, rows_by_id, rows, im.indexes), number=2000)
    t_scan = timeit.timeit(lambda: run_plan(without, rows_by_id, rows, {}), number=2000)
    print(f"[TIMING] 2000 lookups on 1000 rows: index={t_idx:.4f}s  full_scan={t_scan:.4f}s  speedup={t_scan / t_idx:.0f}x")


if __name__ == "__main__":
    main()
